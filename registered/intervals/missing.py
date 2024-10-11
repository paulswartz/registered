"""
Calculate shortest/fastest paths for missing intervals.
"""

import argparse
import csv
from pathlib import Path
import re
from registered.intervals import query
from .interval import Interval
from .cli import page_from_rows, enable_logging, log


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


WHERE = """
(gni.distance_between_measured = 0
  OR gni.distance_between_measured IS NULL)
AND
(gni.distance_between_map = 0
  OR gni.distance_between_map IS NULL)
    """


def read_database():
    """
    Read the missing intervals from the TransitMaster DB.
    """
    return query.read_database(WHERE)


def parse_rows(rows: list[str], include_ignored: bool = False):
    """
    Parse the list of rows into a Page.

    If include_ignored is True, don't filter out ignored intervals.
    """
    if include_ignored:
        interval_filter = None
    else:

        def interval_filter(interval: Interval) -> bool:
            """
            Only keep non-ignored intervals.
            """
            return not should_ignore_interval(interval)

    return page_from_rows(rows, interval_filter=interval_filter)


def main(argv):
    """
    Entrypoint for the Missing Intervals Calculation.
    """
    enable_logging()
    if argv.input_csv:
        log(f"Reading from {argv.input_csv}...")
        rows = list(csv.DictReader(argv.input_csv.open()))
    else:
        log("Reading from TransitMaster database...")
        rows = read_database()
        if argv.output_csv:
            with argv.output_csv.open("w") as out_io:
                headers = rows[0].keys()
                log(f"Writing {len(rows)} to {argv.output_csv}...")
                writer = csv.DictWriter(out_io, headers)
                writer.writeheader()
                writer.writerows(rows)

    page = parse_rows(rows, include_ignored=argv.include_ignored)
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
