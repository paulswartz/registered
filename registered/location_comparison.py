"""
CLI tool to compare locations between the export and TransitMaster.
"""
import argparse
from pyproj import Geod
from registered.rating import Rating
from registered.db import geo_node

GEOD = Geod(ellps="WGS84")


def google_street_view_url(lat, lon):
    """
    Generate a Google Street View URL for a given lat/lon.

    Documentation:
    https://developers.google.com/maps/documentation/urls/get-started#street-view-action
    """
    return f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"


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
    print(
        "stop_id,stop_name,hastus_lat,hastus_lon,tm_lat,tm_lon,distance_m,"
        "hastus_street_view,tm_street_view"
    )
    for stop_id in sorted(stop_ids, key=int):
        stop = stops[stop_id]
        (lat, lon) = stop.latlon()

        if stop_id in tm_stop_locations:
            (tm_lat, tm_lon) = tm_stop_locations[stop_id]
            (_, _, distance) = GEOD.inv(lon, lat, tm_lon, tm_lat)
            distance = f"{int(distance)}"
        else:
            distance = ""
        print(
            f"{stop_id},{stop.name},"
            f"{lat:.6f},{lon:.6f},{tm_lat:.6f},{tm_lon:.6f},{distance},"
            f'"{google_street_view_url(lat,lon)}"',
            f'"{google_street_view_url(tm_lat,tm_lon)}"',
        )


parser = argparse.ArgumentParser(
    description="Compare stops between HASTUS export and TransitMaster"
)
parser.add_argument(
    "DIR", help="The Combine directory where the current rating files live"
)


if __name__ == "__main__":
    import sys

    sys.exit(main(parser.parse_args()))
