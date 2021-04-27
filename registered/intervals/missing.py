"""
Calculate shortest/fastest paths for missing intervals.
"""
import argparse
import csv
from pathlib import Path
import re
import osmnx as ox
from registered import db
from registered.intervals import query
from .page import Page
from .routing import RestrictedGraph, configure_osmnx
from .interval import Interval
from .calculation import IntervalCalculation


IGNORE_RE = re.compile(r"\d|Inbound|Outbound")
IGNORED_PAIRS = {
    ("4191", "4277"),  # N Main St opp Short St to N Main St opp Memorial Pkwy
    (
        "73619",
        "89617",
    ),  # 205 Washington St @ East Walpole Loop to 238 Washington St opp May St
    (
        "109898",
        "109821",
    ),  # Shirley St @ Washington Ave to Veterans Rd @ Washington Ave
    ("censq", "16653"),  # Lynn New Busway to Market St @ Commuter Rail
    ("14748", "censq"),  # Lynn Commuter Rail Busway to Lynn New Busway
    ("fell", "5333"),  # Fellsway Garage to Salem St @ Fellsway Garage
    ("ncamb", "12295"),  # North Cambridge trackless to North Cambridge Carhouse
    ("12295", "ncamb"),  # North Cambridge Carhouse to North Cambridge trackless
}


def should_ignore_interval(interval: Interval) -> bool:
    """
    Return True if we should ignore that the given interval is missing.

    - If the interval is a REVENUE interval (these can be easily calculated in TransitMaster)
    - If the descriptions are the same, except for digits (Busway Berth 1 to Busway Berth 2)
    - If the descriptions are the same, except for Inbound/Outbound
    - If the stops are in one of a few specifically ignored pairs of stops
    """
    from_stop = interval.from_stop
    to_stop = interval.to_stop
    return (from_stop.id, to_stop.id) in IGNORED_PAIRS or IGNORE_RE.sub(
        "", from_stop.description
    ) == IGNORE_RE.sub("", to_stop.description)


def read_database():
    """
    Read the missing intervals from the TransitMaster DB.
    """
    distance = 0
    where = """
(gni.distance_between_measured = ?
  OR gni.distance_between_measured IS NULL)
AND
(gni.distance_between_map = ?
  OR gni.distance_between_map IS NULL)
    """
    return query.read_database(where, (distance, distance))


def parse_rows(rows, include_ignored=False):
    """
    Parse the given list of rows into a Page.
    """
    row_count = len(rows)
    intervals = sorted(Interval.from_row(row) for row in rows)

    if not include_ignored:
        intervals = [
            interval for interval in intervals if not should_ignore_interval(interval)
        ]

    if not intervals:
        ox.utils.log("No intervals to process.")
        return None

    (from_stops, to_stops) = zip(
        *((interval.from_stop, interval.to_stop) for interval in intervals)
    )
    graph = RestrictedGraph.from_points(from_stops + to_stops)

    page = Page(graph=graph)

    for (index, interval) in enumerate(intervals, 1):
        ox.utils.log(f"processing row {index} of {row_count}: {interval!r}")
        calc = IntervalCalculation.calculate(interval=interval, graph=graph)
        page.add(calc)

    return page


def main(argv):
    """
    Entrypoint for the Missing Intervals Calculation.
    """
    configure_osmnx(log_console=True)
    if argv.input_csv:
        ox.utils.log(f"Reading from {argv.input_csv}...")
        rows = list(csv.DictReader(argv.input_csv.open()))
    else:
        ox.utils.log("Reading from TransitMaster database...")
        rows = read_database()
        if argv.output_csv:
            with argv.output_csv.open("w") as out_io:
                headers = rows[0].keys()
                ox.utils.log(f"Writing {len(rows)} to {argv.output_csv}...")
                writer = csv.DictWriter(out_io, headers)
                writer.writeheader()
                writer.writerows(rows)

    page = parse_rows(rows, include_ignored=argv.include_ignored)
    if page:
        with argv.html.open("w") as out_io:
            ox.utils.log(f"Writing HTML to {argv.html}...")
            out_io.write(page.render())


parser = argparse.ArgumentParser(
    description="Calculate missing interval distances and angles."
)
parser.add_argument(
    "html", metavar="HTML", help="path to HTML file to output", type=Path
)
parser.add_argument(
    "--input-csv", type=Path, help="CSV file to use as an input instead of the database"
)
parser.add_argument(
    "--output-csv",
    type=Path,
    help="CSV file to write the database results to (only if reading from the database)",
)
parser.add_argument(
    "--include-ignored",
    action="store_true",
    help="Also include ignored intervals in the HTML output",
)

if __name__ == "__main__":
    main(parser.parse_args())
