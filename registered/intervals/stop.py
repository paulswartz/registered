"""
Calculate shortest/fastest paths for missing intervals.
"""
import argparse
import csv
from pathlib import Path
from typing import Any, List
import osmnx as ox
from registered import db
from registered.intervals import query
from .page import Page
from .routing import RestrictedGraph, configure_osmnx
from .interval import Interval
from .calculation import IntervalCalculation, should_ignore_interval


def read_database(stop_ids: List[str]) -> List[List[Any]]:
    """
    Read the stop intervals from the TransitMaster DB.
    """
    question_marks = ",".join("?" for _ in stop_ids)
    where = f"gn1.geo_node_abbr IN ({question_marks}) or gn2.geo_node_abbr IN ({question_marks})"
    return query.read_database(where, stop_ids + stop_ids)


def parse_rows(rows, include_ignored=False):
    """
    Parse the given list of rows into a Page.
    """
    row_count = len(rows)
    intervals = sorted(Interval.from_row(row) for row in rows)

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
    Entrypoint for the Stop Intervals Calculation.
    """
    configure_osmnx(log_console=True)
    if argv.input_csv:
        ox.utils.log(f"Reading from {argv.input_csv}...")
        rows = list(csv.DictReader(argv.input_csv.open()))
    else:
        ox.utils.log("Reading from TransitMaster database...")
        stop_ids = []
        if argv.stop_id:
            stop_ids += argv.stop_id
        if argv.stop_id_csv:
            stop_ids += (row[0] for row in csv.reader(argv.stop_id_csv.open()))
        rows = read_database(stop_ids)
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
    "--stop-id",
    metavar="STOP_ID",
    help="Stop ID to find intervals for",
    action="append",
)
parser.add_argument(
    "--stop-id-csv", metavar="CSV", help="CSVs with stop IDs in first column", type=Path
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
