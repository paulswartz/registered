"""
Calculate shortest/fastest paths for missing intervals.
"""
import argparse
import csv
from pathlib import Path
import osmnx as ox
from registered import db
from .page import Page
from .routing import RestrictedGraph, configure_osmnx
from .interval import Interval
from .calculation import IntervalCalculation, should_ignore_interval


def read_database():
    """
    Read the missing intervals from the TransitMaster DB.
    """
    # 8/20/18 Updated by Jennette Rodemeyer to exclude "and
    # (gni.compass_direction is not null)", since TM17 sets new deadhead
    # intervals to null heading by default. */
    sql = """
SET NOCOUNT ON;

declare @ttvid numeric(9);
select @ttvid = max(time_table_version_id) from time_table_version;

declare @distval numeric(6);
SELECT @distval = 0;  -- Distance in feet to look for.

select
	1 as issueid,
	@ttvid + 0.2 as routeversionid,
    gni.interval_id as IntervalId,
	0 AS IntervalType,
	gn1.geo_node_abbr AS FromStopNumber,
	gn1.geo_node_name AS FromStopDescription,
	gn1.mdt_latitude/10000000 as FromStopLatitude,
	gn1.mdt_longitude/10000000 as FromStopLongitude,
	gn2.geo_node_abbr AS ToStopNumber,
	gn2.geo_node_name AS ToStopDescription,
	gn2.mdt_latitude/10000000 as ToStopLatitude,
	gn2.mdt_longitude/10000000 as ToStopLongitude,
	min(RTRIM(r.route_abbr) + '-' + RTRIM(rd.route_direction_name) + '-' + RTRIM(p.pattern_abbr)) AS IntervalDescription
from
	pattern_geo_interval_xref pgix
inner join pattern p on
	pgix.pattern_id = p.pattern_id
inner join route r on
	p.route_id = r.route_id
inner join route_direction rd on
	p.route_direction_id = rd.route_direction_id
inner join geo_node_interval gni on
	pgix.geo_node_interval_id = gni.interval_id
inner join geo_node gn1 on
	gni.start_point_id = gn1.geo_node_id
inner join geo_node gn2 on
	gni.end_point_id = gn2.geo_node_id
where
	pgix.time_table_version_id = @ttvid
	AND ( gni.distance_between_measured = @distval
		OR gni.distance_between_measured IS NULL )
	AND ( gni.distance_between_map = @distval
		OR gni.distance_between_map IS NULL )
group by
	gn1.geo_node_abbr,
	gn1.geo_node_name,
	gn1.mdt_latitude,
	gn1.mdt_longitude,
	gn2.geo_node_abbr,
	gn2.geo_node_name,
	gn2.mdt_latitude,
	gn2.mdt_longitude
UNION
select
	1 as issueid,
	@ttvid + 0.2 as routeversionid,
    gni.interval_id as IntervalId,
    DH_TYPE as IntervalType,
	gn1.geo_node_abbr AS FromStopNumber,
	gn1.geo_node_name AS FromStopDescription,
	gn1.mdt_latitude/10000000 as FromStopLatitude,
	gn1.mdt_longitude/10000000 as FromStopLongitude,
	gn2.geo_node_abbr AS ToStopNumber,
	gn2.geo_node_name AS ToStopDescription,
	gn2.mdt_latitude/10000000 as ToStopLatitude,
	gn2.mdt_longitude/10000000 as ToStopLongitude,
	MIN(RTRIM(r.route_abbr) + '-' + RTRIM(rd.route_direction_name) + '-' + RTRIM(p.pattern_abbr)) AS IntervalDescription
from
	deadheads dh
inner join pattern p on
	dh.pattern_id = p.pattern_id
inner join route r on
	p.route_id = r.route_id
inner join route_direction rd on
	p.route_direction_id = rd.route_direction_id
inner join geo_node_interval gni on
	dh.geo_node_interval_id = gni.interval_id
inner join geo_node gn1 on
	gni.start_point_id = gn1.geo_node_id
inner join geo_node gn2 on
	gni.end_point_id = gn2.geo_node_id
where
	dh.time_table_version_id = @ttvid
	AND ( gni.distance_between_measured = @distval
		OR gni.distance_between_measured IS NULL )
	AND ( gni.distance_between_map = @distval
		OR gni.distance_between_map IS NULL )
group by
	dh_type,
	gn1.geo_node_abbr,
	gn1.geo_node_name,
	gn1.mdt_latitude,
	gn1.mdt_longitude,
	gn2.geo_node_abbr,
	gn2.geo_node_name,
	gn2.mdt_latitude,
	gn2.mdt_longitude
order by
	IntervalType,
	IntervalDescription;
    """
    conn = db.conn()
    cursor = conn.cursor()
    cursor.execute(sql)
    sql_headers = [desc[0] for desc in cursor.description]
    result = cursor.fetchall()
    return [dict(zip(sql_headers, row)) for row in result]


def parse_rows(rows, include_ignored=False):
    """
    Parse the given list of rows into a Page.
    """
    row_count = len(rows)
    intervals = [Interval.from_row(row) for row in rows]

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
