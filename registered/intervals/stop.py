"""
Calculate shortest/fastest paths for missing intervals.
"""
import argparse
import csv
from pathlib import Path
from typing import Any, List
from registered.intervals import query
from .cli import page_from_rows, enable_logging, log


def read_database(stop_ids: List[str]) -> List[List[Any]]:
    """
    Read the stop intervals from the TransitMaster DB.
    """
    question_marks = ",".join("?" for _ in stop_ids)
    where = f"gn1.geo_node_abbr IN ({question_marks}) or gn2.geo_node_abbr IN ({question_marks})"
    return query.read_database(where, stop_ids + stop_ids)


def main(argv):
    """
    Entrypoint for the Stop Intervals Calculation.
    """
    enable_logging()
    if argv.input_csv:
        log(f"Reading from {argv.input_csv}...")
        rows = list(csv.DictReader(argv.input_csv.open()))
    else:
        log("Reading from TransitMaster database...")
        stop_ids = []
        if argv.stop_id:
            stop_ids += argv.stop_id
        if argv.stop_id_csv:
            stop_ids += (row[0] for row in csv.reader(argv.stop_id_csv.open()))
        rows = read_database(stop_ids)
        if argv.output_csv:
            with argv.output_csv.open("w") as out_io:
                headers = rows[0].keys()
                log(f"Writing {len(rows)} to {argv.output_csv}...")
                writer = csv.DictWriter(out_io, headers)
                writer.writeheader()
                writer.writerows(rows)

    page = page_from_rows(rows)
    if page:
        with argv.html.open("w") as out_io:
            log(f"Writing HTML to {argv.html}...")
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

if __name__ == "__main__":
    main(parser.parse_args())
