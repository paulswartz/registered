"""
CLI tool to compare the stops between two ratings.
"""
import argparse
from collections import defaultdict
from registered.parser import Pattern, PatternStop
from registered.rating import Rating


def output(stops, stop_ids, by_stop, change_type):
    """
    Output given stops in the appropriate TSV format.
    """
    for stop_id in sorted(stop_ids, key=int):
        stop = stops[stop_id]
        (lat, lon) = stop.latlon()
        route_directions = ", ".join(
            f"{route_id} {direction_name}"
            for (route_id, direction_name) in sorted(by_stop[stop_id])
        )
        print(
            f'{stop_id},{stop.name},{change_type},{lat:5f},{lon:5f},"{route_directions}"'
        )


def route_direction_by_stops(rating):
    """
    Given a Rating, return a dictionary mapping stop IDs to the route/directions which use it.
    """
    last_key = None
    by_stop = defaultdict(set)
    for record in rating["pat"]:
        if isinstance(record, Pattern):
            last_key = (record.route_id, record.direction_name)
            continue

        if isinstance(record, PatternStop):
            by_stop[record.stop_id].add(last_key)

    return by_stop


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    current_rating = Rating(args.CURRENT)
    next_rating = Rating(args.NEXT)
    by_stop = route_direction_by_stops(next_rating)

    current_rating_stops = {stop.stop_id: stop for stop in current_rating["nde"]}
    current_rating_stop_ids = set(current_rating_stops)

    next_rating_stops = {stop.stop_id: stop for stop in next_rating["nde"]}
    next_rating_stop_ids = set(next_rating_stops)

    new_stop_ids = next_rating_stop_ids - current_rating_stop_ids
    output(next_rating_stops, new_stop_ids, by_stop, "newStops")

    shared_stop_ids = next_rating_stop_ids & current_rating_stop_ids
    same_names = {
        stop_id
        for stop_id in shared_stop_ids
        if current_rating_stops[stop_id].name == next_rating_stops[stop_id].name
    }
    same_locations = {
        stop_id
        for stop_id in shared_stop_ids
        if (
            current_rating_stops[stop_id].easting_ft,
            current_rating_stops[stop_id].northing_ft,
        )
        == (
            next_rating_stops[stop_id].easting_ft,
            next_rating_stops[stop_id].northing_ft,
        )
    }

    output(
        next_rating_stops,
        shared_stop_ids - same_names - same_locations,
        by_stop,
        "newName_newLocation",
    )
    output(
        next_rating_stops, same_names - same_locations, by_stop, "sameName_newLocation"
    )
    output(
        next_rating_stops, same_locations - same_names, by_stop, "newName_sameLocation"
    )


parser = argparse.ArgumentParser(
    description="Compare two ratings to find new/modified stops."
)
parser.add_argument(
    "CURRENT", help="The Combine directory where the current rating files live"
)
parser.add_argument(
    "NEXT", help="The Combine directory where the next rating files live"
)

if __name__ == "__main__":
    import sys

    sys.exit(main(parser.parse_args()))
