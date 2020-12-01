"""
CLI tool to compare locations between the export and TransitMaster.
"""
import argparse
from pyproj import Geod
from registered.rating import Rating
from registered.db import geo_node

GEOD = Geod(ellps="WGS84")


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    rating = Rating(args.DIR)

    stops = {
        stop.stop_id: stop
        for stop in rating["nde"]
        if stop.easting_ft and stop.northing_ft
    }
    stop_ids = set(stops)
    tm_stop_locations = {
        stop_id: (lat, lon)
        for (stop_id, _, lat, lon) in geo_node(stop_ids)
        if lat and lon
    }
    for stop_id in sorted(stop_ids, key=int):
        stop = stops[stop_id]
        (lat, lon) = stop.latlon()

        if stop_id in tm_stop_locations:
            (tm_lat, tm_lon) = tm_stop_locations[stop_id]
            (_, _, distance) = GEOD.inv(lon, lat, tm_lon, tm_lat)
            distance = f"{int(distance)}"
        else:
            distance = ""
        print(f"{stop_id},{stop.name}," f"{lat:.5f},{lon:.5f},{distance}")


parser = argparse.ArgumentParser(
    description="Compare stops between HASTUS export and TransitMaster"
)
parser.add_argument(
    "DIR", help="The Combine directory where the current rating files live"
)


if __name__ == "__main__":
    import sys

    sys.exit(main(parser.parse_args()))
