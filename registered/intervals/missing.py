"""
Calculate shortest/fastest paths for missing intervals.
"""
import argparse
import csv
from pathlib import Path
import re
from typing import Optional, List, Tuple
import attr
import osmnx as ox
from jinja2 import Template
from registered import db
from .routing import RestrictedGraph, configure_osmnx
from .interval import Interval
from .calculation import IntervalCalculation, should_ignore_interval


@attr.define
class Page:
    """
    A full HTML page of interval calculations.
    """

    _graph: RestrictedGraph
    calculations: List[IntervalCalculation] = attr.ib(factory=list)

    def add(self, calculation: IntervalCalculation):
        """
        Add an interval to the page for future rendering.
        """
        self.calculations.append(calculation)

    _template = Template(
        """
    <!DOCTYPE html>
    <html>
    <head>
      <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
      <meta name="viewport" content="width=device-width,
            initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <style type="text/css">
        html {
          padding: 2em;
        }
        td {
          padding: 0 3em 1em;
        }
        td:first-child {
          padding-left: 0;
        }
        .folium-map {
          display: block;
          height: 50em;
          width: 50em;
        }
      </style>

      <script>
        L_NO_TOUCH = false;
        L_DISABLE_3D = false;
      </script>

      {% for script in scripts %}<script defer src="{{script}}"></script>{% endfor %}
      {% for sheet in stylesheets %}<link rel="stylesheet" href="{{sheet}}"/>{% endfor %}
    </head>
    <body>
      {% for calculation in this.calculations %}
      {% if loop.index > 1 %}<hr>{% endif %}
      {{ this.render_calculation(calculation) }}
      {% endfor %}
    </body>
    </html>
    """
    )

    _calculation_template = Template(
        """
    <div>
      <table>
        <thead>
          <tr>
            <th>From</th>
            <th>To</th>
            <th>Interval Type</th>
            <th>Description</th>
            <th>Directions</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{{ page.render_stop(this.from_stop) }}</td>
            <td>{{ page.render_stop(this.to_stop) }}</td>
            <td>{{ this.interval_type}}</td>
            <td>{{ this.description }}</td>
            <td>
              <a target="_blank"
                 href="{{ google_maps_url | e}}">Google Maps</a><br>
              <a target="_blank"
                 href="{{ osm_url | e}}">OpenStreetMap</a><br>
            </td>
          </tr>
        </tbody>
      </table>
      <table>
        <thead>
          <tr>
            <th>Route</th>
            <th>Length (ft)</th>
            <th>Compass Direction</th>
          </tr>
        </thead>
        <tbody>
        {% for item in results %}
          <tr>
             {% for cell in item %}<td>{{ cell }}</td>{% endfor %}
          </tr>
        {% endfor %}
        </tbody>
      </table>
      {{ folium_map_html }}
      <script type="text/javascript">
        window.addEventListener('DOMContentLoaded', function() {
          {{ folium_map_script }}
        });
      </script>
    </div>
    """
    )

    _stop_template = Template(
        """
    {{ this.description }} ({{ this.id }})<br>
    <a href="{{osm_url | e}}">OpenStreetMap</a>
    """
    )

    def render_calculation(self, calculation: IntervalCalculation) -> str:
        """
        Render the calculation as HTML.
        """
        google_maps_url = self._google_maps_url(
            calculation.from_stop, calculation.to_stop
        )
        osm_url = self._osm_url(calculation.from_stop, calculation.to_stop)
        results = self._calculate_results(calculation)
        folium_map = self._graph.folium_map(
            calculation.from_stop, calculation.to_stop, calculation.paths()
        )

        folium_map.render()
        map_root = folium_map.get_root()
        folium_map_html = map_root.html.render()
        folium_map_script = map_root.script.render()

        return self._calculation_template.render(
            page=self,
            this=calculation,
            google_maps_url=google_maps_url,
            osm_url=osm_url,
            results=results,
            folium_map_html=folium_map_html,
            folium_map_script=folium_map_script,
        )

    def _calculate_results(
        self, calculation: IntervalCalculation
    ) -> List[Tuple[str, str, str]]:
        named_paths = zip(["Fastest (red)", "Shortest (yellow)"], calculation.paths())
        if not named_paths:
            return [("", "0", "NULL")]
        return [
            (
                name,
                str(self.meters_to_feet(self._graph.path_length(path))),
                str(self._graph.compass_direction(path)),
            )
            for (name, path) in named_paths
        ]

    @staticmethod
    def _google_maps_url(from_stop, to_stop):
        return (
            f"https://www.google.com/maps/dir/?api=1&"
            f"travelmode=driving&"
            f"origin={ from_stop.y },{ from_stop.x }&"
            f"destination={ to_stop.y },{ to_stop.x }"
        )

    @staticmethod
    def _osm_url(from_stop, to_stop):
        return (
            f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&"
            f"route={from_stop.y},{from_stop.x};{to_stop.y},{to_stop.x}"
        )

    @classmethod
    def render_stop(cls, stop):
        """
        Render a stop to HTML.
        """
        osm_url = (
            f"https://www.openstreetmap.org/query?"
            f"lat={stop.y}&lon={stop.x}"
            f"#map=18/{stop.y}/{stop.x}"
        )
        return cls._stop_template.render(this=stop, osm_url=osm_url)

    @staticmethod
    def meters_to_feet(meters):
        """
        Convert the given distance in meters to feet.
        """
        return int(meters * 3.281)

    def render(self):
        """
        Render to HTML.
        """
        # pylint: disable=line-too-long
        ox.utils.log("rendering page...")
        scripts = [
            "https://cdn.jsdelivr.net/npm/leaflet@1.6.0/dist/leaflet.js",
            "https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js",
        ]
        stylesheets = [
            "https://cdn.jsdelivr.net/npm/leaflet@1.6.0/dist/leaflet.css",
            "https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css",
            "https://maxcdn.bootstrapcdn.com/font-awesome/4.6.3/css/font-awesome.min.css",
            "https://maxcdn.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap-glyphicons.css",
        ]
        return self._template.render(
            this=self, scripts=scripts, stylesheets=stylesheets
        )


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
