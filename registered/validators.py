"""
Collection of validators for rating data.
"""
from collections import defaultdict
import attr
from registered import parser


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

    for (key, pattern_ids) in patterns_by_prefix.items():
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

    for (timepoint_pattern_id, patterns) in patterns_by_id.items():
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
    timepoints_by_route_direction = {}
    for timepoint_pattern in rating["ppat"]:
        key = (timepoint_pattern.route_id, timepoint_pattern.direction_name)
        timepoints_by_route_direction[key] = set(timepoint_pattern.timepoints)

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


ALL_VALIDATORS = [
    validate_unique_pattern_prefix,
    validate_unique_timepoint_pattern,
    validate_no_extra_timepoints,
]
