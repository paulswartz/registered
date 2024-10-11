"""
Collection of validators for rating data.
"""

from collections import defaultdict
import itertools
import attr
from registered import parser
from registered.validate import helpers


@attr.s(frozen=True)
class ValidationError:  # pylint: disable=too-few-public-methods
    """
    Wrapper around a single instance of a validation error.
    """

    file_type = attr.ib()
    key = attr.ib()
    error = attr.ib()
    description = attr.ib()


def validate_unique_pattern_prefix(rating):
    """
    For most patterns in PAT file, the pattern prefix (first 5 characters) and direction are unique.
    """
    expected_non_unique_keys = [
        ("00wad", "Inbound"),
        ("00rad", "Inbound"),
        ("00wad", "Outbound"),
        ("00rad", "Outbound"),
        ("0746_", "Inbound"),
        ("0746_", "Outbound"),
    ]
    patterns_by_prefix = defaultdict(set)
    for parsed in rating["pat"]:
        if not isinstance(parsed, parser.Pattern):
            continue
        if parsed.direction_name == "":
            # ignore blanks
            continue
        key = (parsed.pattern_id[:5], parsed.direction_name)
        if key in expected_non_unique_keys:
            continue

        patterns_by_prefix[key].add(parsed.pattern_id)

    for key, pattern_ids in patterns_by_prefix.items():
        if len(pattern_ids) == 1:
            continue

        yield ValidationError(
            file_type="pat",
            key=key,
            error="non_unique_pattern",
            description=f"multiple patterns with prefix: {list(pattern_ids)}",
        )


def validate_unique_timepoint_pattern(rating):
    """
    For a given timepoint pattern ID, the list of timepoints should be always be the same.
    """
    patterns_by_id = defaultdict(list)
    for timepoint_pattern in rating["ppat"]:
        patterns_by_id[timepoint_pattern.timepoint_pattern_id].append(timepoint_pattern)

    for timepoint_pattern_id, patterns in patterns_by_id.items():
        if len(patterns) == 1:
            continue
        [first, *rest] = patterns
        for pattern in rest:
            if first.timepoints != pattern.timepoints:
                yield ValidationError(
                    file_type="ppat",
                    key=timepoint_pattern_id,
                    error="non_unique_timepoint_pattern",
                    description=f"{first.timepoints} != {pattern.timepoints}",
                )


def validate_no_extra_timepoints(rating):
    """
    All timepoints in PAT should also be in PPAT for a given route/direction.

    Exceptions:
    - PPAT records with an empty direction_name
    - RAD/WAD routes
    """
    timepoints_by_route_direction = helpers.timepoints_by_route_direction(rating)

    key = None
    for record in rating["pat"]:
        # keep track of the last Pattern we saw
        if isinstance(record, parser.Pattern):
            if record.route_id in {"rad", "wad"}:
                # RAD/WAD routes don't need to get validated
                key = None
                continue

            key = (record.route_id, record.direction_name)
            if key not in timepoints_by_route_direction and record.direction_name != "":
                yield ValidationError(
                    file_type="pat",
                    key=key,
                    error="timepoint_pattern_missing",
                    description="No matching timepoint pattern found",
                )
            continue
        # record is a PatternStop
        if key is None or key not in timepoints_by_route_direction:
            # missing route/directions already provided a ValidationError above
            continue
        if not record.is_timepoint:
            continue

        timepoint = record.timepoint_id
        if timepoint not in timepoints_by_route_direction[key]:
            yield ValidationError(
                file_type="pat",
                key=key,
                error="timepoint_missing_from_timepoint_pattern",
                description=f"{repr(timepoint)} missing from timepoint patterns",
            )


def validate_timepoints_in_consistent_order(rating):
    """
    Timepoints in PAT should be in the same order as in PPAT for a given route/direction.
    """
    timepoints_by_route_direction = helpers.timepoints_by_route_direction(rating)

    pattern = None
    timepoints = []

    def validate_timepoints():
        key = (pattern.route_id, pattern.direction_name)
        expected_timepoints = timepoints_by_route_direction.get(key, [])

        if expected_timepoints == []:
            return  # pylint: disable

        filtered_timepoints = [
            timepoint for timepoint in timepoints if timepoint in expected_timepoints
        ]
        if not helpers.same_list_order(expected_timepoints, filtered_timepoints):
            yield ValidationError(
                file_type="pat",
                key=pattern.pattern_id,
                error="timepoints_out_of_order",
                description=(
                    f"expected timepoint order: {repr(expected_timepoints)} "
                    f"actual timepoint order: {repr(filtered_timepoints)}"
                ),
            )

    for record in rating["pat"]:
        if isinstance(record, parser.Pattern):
            if pattern:
                yield from validate_timepoints()

            pattern = record
            timepoints = []
            continue

        if isinstance(record, parser.PatternStop) and record.timepoint_id:
            timepoints.append(record.timepoint_id)

    if pattern:
        yield from validate_timepoints()


VALID_GARAGES = {
    "albny",
    "arbor",
    "cabot",
    "censq",
    "charl",
    "fell",
    "lynn",
    "marbl",
    "ncamb",
    "ngate",
    "prwb",
    "soham",
    "qubus",
    "somvl",
    "wondw",
}


def validate_block_garages(rating):
    """
    Validate that each block leaves/arrives from the same, valid, garage.

    Exceptions:
    - Central Square -> Lynn
    - Lynn -> Central Square
    - Lynn -> Wonderland
    - Wonderland -> Lynn
    - dead reckoning schedules (ST1, DR1)
    """
    for record in rating["blk"]:
        if not isinstance(record, parser.Block):
            continue

        if record.service_key in {"ST1", "DR1"}:
            continue

        (first_garage, _) = record.times[0]
        (last_garage, _) = record.times[-1]

        for garage in [first_garage, last_garage]:
            if garage not in VALID_GARAGES:
                yield ValidationError(
                    file_type="blk",
                    key=(record.block_id, record.service_key),
                    error="block_with_invalid_garage",
                    description=f"{garage} is not a valid garage",
                )

        if first_garage != last_garage and (first_garage, last_garage) not in {
            ("censq", "lynn"),
            ("lynn", "censq"),
            ("lynn", "ngate"),
            ("lynn", "wondw"),
            ("marbl", "lynn"),
            ("ngate", "lynn"),
            ("wondw", "lynn"),
        }:
            yield ValidationError(
                file_type="blk",
                key=(record.block_id, record.service_key),
                error="block_with_different_garage",
                description=f"leaves from {first_garage}, arrives at {last_garage}",
            )


def validate_all_blocks_have_trips(rating):
    """
    Validate that all blocks have at least one revenue trip.

    Exceptions:
    - RAD/WAD blocks
    """
    previous_block = None
    has_revenue_trips = False

    revenue_trips = {
        trip.trip_id
        for trip in rating["trp"]
        if isinstance(trip, parser.Trip)
        and trip.trip_type in {parser.TripType.REGULAR, parser.TripType.OPPORTUNITY}
    }

    def error():
        return ValidationError(
            file_type="blk",
            key=(previous_block.block_id, previous_block.service_key),
            error="block_with_no_trips",
            description="Block has no/only non-revenue trips",
        )

    for record in rating["blk"]:
        if isinstance(record, parser.Block):
            if "rad" in record.block_id or "wad" in record.block_id:
                # don't need to validate RAD/WAD trips.
                previous_block = None
                has_revenue_trips = False
                continue

            if previous_block is not None and not has_revenue_trips:
                yield error()

            previous_block = record
            has_revenue_trips = False
            continue

        if previous_block is None:
            continue

        if isinstance(record, parser.TripIdentifier):
            if record.trip_id in revenue_trips:
                has_revenue_trips = True

    if not has_revenue_trips and previous_block is not None:
        yield error()


def validate_trip_has_valid_pattern(rating):
    """
    Validate that each trip's pattern is also present in the PAT file.

    Exceptions:
    - non revenue trips
    - as-directed trips
    """
    valid_patterns = {
        pattern.pattern_id
        for pattern in rating["pat"]
        if isinstance(pattern, parser.Pattern)
    }

    invalid_trips = (
        trip
        for trip in rating["trp"]
        if isinstance(trip, parser.Trip)
        and trip.pattern_id not in valid_patterns
        and not trip.as_directed
        and (
            trip.trip_type == parser.TripType.REGULAR
            or trip.trip_type == parser.TripType.OPPORTUNITY
        )
    )

    for trip in invalid_trips:
        yield ValidationError(
            file_type="trp",
            key=trip.trip_id,
            error="trip_with_invalid_pattern",
            description=f"pattern {trip.pattern_id} does not exist",
        )


def validate_all_revenue_trips_are_public(rating):
    """
    Validate that each trip is tagged as public.

    Exceptions:
    - non revenue trips, as-directed trips, test trips
    """

    non_public_revenue_trips = (
        trip
        for trip in rating["trp"]
        if isinstance(trip, parser.Trip)
        and trip.public_type == parser.PublicType.NON_PUBLIC
        and not trip.as_directed
        and (
            trip.trip_type == parser.TripType.REGULAR
            or trip.trip_type == parser.TripType.OPPORTUNITY
        )
    )

    for trip in non_public_revenue_trips:
        yield ValidationError(
            file_type="trp",
            key=trip.trip_id,
            error="trip_revenue_and_non_public",
            description=f"trip {trip.trip_id} is revenue but non-public",
        )


def validate_stop_has_only_one_timepoint(rating):
    """
    Stops should only have one timepoint value.
    """
    stop_timepoints = defaultdict(set)
    for stop in rating["nde"]:
        if stop.timepoint_id == "":
            continue
        # add the default timepoint if the stop exists in the NDE file
        stop_timepoints[stop.stop_id].add(stop.timepoint_id)

    for record in rating["pat"]:
        if not isinstance(record, parser.PatternStop):
            continue

        if record.timepoint_id == "":
            continue

        stop_timepoints[record.stop_id].add(record.timepoint_id)

    for stop_id, timepoints in stop_timepoints.items():
        if len(timepoints) == 1:
            continue

        yield ValidationError(
            file_type="pat",
            key=stop_id,
            error="stop_with_multiple_timepoints",
            description=repr(timepoints),
        )


def validate_all_routes_have_patterns(rating):
    """
    All routes (RTE file) should have at least one pattern.
    """
    routes = {route.route_id for route in rating["rte"]}

    routes_from_patterns = {
        record.route_id
        for record in rating["pat"]
        if isinstance(record, parser.Pattern)
    }

    missing_routes = routes - routes_from_patterns
    for route_id in missing_routes:
        yield ValidationError(
            file_type="rte",
            key=route_id,
            error="route_without_patterns",
            description="route has no patterns in PAT file",
        )


def validate_pattern_stop_has_node(rating):
    """
    All PatternStop records should exist in the NDE file.
    """
    valid_stops = {stop.stop_id for stop in rating["nde"]}

    pattern = None
    for record in rating["pat"]:
        if isinstance(record, parser.Pattern):
            pattern = record
            continue

        if not isinstance(record, parser.PatternStop):
            continue

        if record.stop_id not in valid_stops:
            yield ValidationError(
                file_type="pat",
                key=(pattern.pattern_id, record.stop_id),
                error="pattern_stop_without_node",
                description=f"stop {record.stop_id} not in NDE file",
            )


def validate_routes_have_two_directions(rating):
    """
    Each route in the PPAT file should have two directions.

    Exceptions:
    - 171
    - 195
    - 214
    - 600 (Onboard Tablet Pilot Test Route)
    - 601 (Onboard Tablet Pilot Test Route)
    - rad
    - wad
    """
    default_expected_count = 2
    override_counts = {
        "171": 1,
        "195": 1,
        "214": 1,
        "600": 1,
        "601": 1,
        "rad": 1,
        "wad": 1,
    }
    routes_to_directions = defaultdict(set)

    for trip_pattern in rating["ppat"]:
        routes_to_directions[trip_pattern.route_id].add(trip_pattern.direction_name)

    for route_id, direction_names in routes_to_directions.items():
        expected_count = override_counts.get(route_id, default_expected_count)

        if len(direction_names) == expected_count:
            continue

        yield ValidationError(
            file_type="ppat",
            key=route_id,
            error="route_with_unexpected_direction_count",
            description=f"has directions {repr(direction_names)}",
        )


def validate_all_blocks_have_runs(rating):
    """
    Each block in the BLK file should have at least one Piece in the CRW file.
    """
    piece_id_service_keys = {
        (piece.piece_id, piece.service_key)
        for piece in rating["crw"]
        if isinstance(piece, parser.Piece)
    }

    for block in rating["blk"]:
        if not isinstance(block, parser.Block):
            continue

        if (block.piece_id, block.service_key) in piece_id_service_keys:
            continue

        yield ValidationError(
            file_type="blk",
            error="block_without_runs",
            key=(block.block_id, block.service_key),
            description="No pieces found.",
        )


def validate_all_runs_have_blocks(rating):
    """
    Each block in the BLK file should have at least one Piece in the CRW file.
    """
    piece_id_service_keys = {
        (block.piece_id, block.service_key)
        for block in rating["blk"]
        if isinstance(block, parser.Block)
    }

    for piece in rating["crw"]:
        if not isinstance(piece, parser.Piece):
            continue

        if (piece.piece_id, piece.service_key) in piece_id_service_keys:
            continue

        yield ValidationError(
            file_type="crw",
            error="run_without_blocks",
            key=(piece.run_id, piece.service_key),
            description="No blocks found.",
        )


def validate_calendar_exceptions_have_unique_runs(rating):
    """
    Validate that each used exception combo has unique run IDs.

    Inside TransitMaster, we only use the last 3 digits of the service ID to
    identify which blocks/runs are active. Inside HASTUS, the schedulers need
    to be aware of this, so that those groups use a unique set of runs. If they
    are not, it can cause an issue where overlapping runs are activated inside
    TM on a particular date, causing lots of problems.
    """
    calendar_dates_to_exceptions = defaultdict(set)
    for record in rating["cal"]:
        if not isinstance(record, parser.CalendarDate):
            continue
        if record.service_key == "":
            # Service not active on the date
            continue
        calendar_dates_to_exceptions[record.date].add(record.service_key)
    possible_exceptions = {
        frozenset(combo) for combo in calendar_dates_to_exceptions.values()
    }

    runs_by_service_key = defaultdict(set)
    for record in rating["crw"]:
        if not isinstance(record, parser.Piece):
            continue

        runs_by_service_key[record.service_key].add(record.run_id)

    for combo in possible_exceptions:
        if len(combo) == 1:
            continue
        for fst, snd in itertools.combinations(combo, 2):
            overlaps = runs_by_service_key[fst] & runs_by_service_key[snd]
            for run_id in overlaps:
                yield ValidationError(
                    file_type="crw",
                    error="calendar_exception_with_duplicate_runs",
                    key=run_id,
                    description=f"used by services: {fst}, {snd}",
                )


def validate_services_have_unique_blocks(rating):
    """
    Validate that each used service ID has unique block IDs.

    Inside TransitMaster, we only use the last 3 digits of the service ID to
    identify which blocks/runs are active.
    """
    seen = set()
    for record in rating["blk"]:
        if not isinstance(record, parser.Block):
            continue
        key = (record.block_id, record.service_key)
        if key in seen:
            yield ValidationError(
                file_type="blk",
                error="duplicate_block_on_service",
                key=key,
                description="",
            )
        else:
            seen.add(key)


ALL_VALIDATORS = [
    validate_all_blocks_have_trips,
    validate_all_blocks_have_runs,
    validate_all_revenue_trips_are_public,
    validate_all_routes_have_patterns,
    validate_all_runs_have_blocks,
    validate_block_garages,
    validate_calendar_exceptions_have_unique_runs,
    validate_services_have_unique_blocks,
    validate_no_extra_timepoints,
    validate_pattern_stop_has_node,
    validate_routes_have_two_directions,
    validate_stop_has_only_one_timepoint,
    validate_timepoints_in_consistent_order,
    validate_trip_has_valid_pattern,
    validate_unique_pattern_prefix,
    validate_unique_timepoint_pattern,
]
