"""
Calculate shortest/fastest paths for missing intervals.
"""
import argparse
import csv
from pathlib import Path
import re
import attr
import osmnx as ox
from jinja2 import Template
from shapely.geometry import Point
import networkx as nx
from registered import db, routing


class Stop(Point):  # pylint: disable=too-few-public-methods
    """
    A location to calculate an interval (either from or to).
    """

    def __init__(
        self, id, description, mdt_latitude, mdt_longitude=None
    ):  # pylint: disable=redefined-builtin
        """
        Initialize our Stop with the extra parameters.
        """
        if mdt_longitude is None:
            Point.__init__(self, mdt_latitude)
        else:
            Point.__init__(self, (float(mdt_longitude), float(mdt_latitude)))
        self.id = id  # pylint: disable=invalid-name
        self.description = description

    _template = Template(
        """
    {{ this.description }} ({{ this.id }})<br>
    <a href="{{osm_url | e}}">OpenStreetMap</a>
    """
    )

    def __repr__(self):
        return (
            f"Stop(id={self.id!r}, description={self.description!r}, point={self.wkt})"
        )

    def render(self):
        """
        Render to HTML.
        """
        osm_url = (
            f"https://www.openstreetmap.org/query?"
            f"lat={self.y}&lon={self.x}"
            f"#map=18/{self.y}/{self.x}"
        )
        return self._template.render(this=self, osm_url=osm_url)


@attr.s
class Interval:  # pylint: disable=too-many-instance-attributes
    """
    One interval calculation.
    """

    from_stop = attr.ib()
    to_stop = attr.ib()
    interval_type = attr.ib()
    description = attr.ib()
    graph = attr.ib(default=None)
    fastest_path = attr.ib(default=None)
    shortest_path = attr.ib(default=None)
    folium_map = attr.ib(default=None)

    # pylint: disable=too-many-arguments
    @classmethod
    def from_stops(cls, from_stop, to_stop, graph, interval_type, interval_description):
        """
        Create an interval given the from/to stops.
        """
        fastest_path = shortest_path = None
        if not cls.should_ignore(from_stop, to_stop):
            ox.utils.log(f"calculating interval from {from_stop} to {to_stop}")
            try:
                fastest_path = graph.shortest_path(from_stop, to_stop)
                shortest_path = graph.shortest_path(from_stop, to_stop, weight="length")
            except nx.NetworkXNoPath:
                pass

        if fastest_path == shortest_path:
            shortest_path = None

        paths = [path for path in [fastest_path, shortest_path] if path is not None]

        folium_map = graph.folium_map(
            from_stop,
            to_stop,
            paths,
            height=600,
            width=600,
        )

        return cls(
            from_stop,
            to_stop,
            interval_type,
            interval_description,
            graph,
            fastest_path,
            shortest_path,
            folium_map,
        )

    IGNORE_RE = re.compile(r"\d|Inbound|Outbound")

    @classmethod
    def should_ignore(cls, from_stop, to_stop):
        """
        Return True if we should ignore the given interval.

        - If the descriptions are the same, except for digits (Busway Berth 1 to Busway Berth 2)
        """
        return cls.IGNORE_RE.sub("", from_stop.description) == cls.IGNORE_RE.sub(
            "", to_stop.description
        )

    _template = Template(
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
            <td>{{ this.from_stop.render() }}</td>
            <td>{{ this.to_stop.render() }}</td>
            <td>{{ this.interval_type }}</td>
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

    def render(self):
        """
        Render to HTML.
        """
        google_maps_url = (
            f"https://www.google.com/maps/dir/?api=1&"
            f"travelmode=driving&"
            f"origin={ self.from_stop.y },{ self.from_stop.x }&"
            f"destination={ self.to_stop.y },{ self.to_stop.x }"
        )
        osm_url = (
            f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&"
            f"route={self.from_stop.y},{self.from_stop.x};{self.to_stop.y},{self.to_stop.x}"
        )
        results = self._calculate_results()
        self.folium_map.render()
        map_root = self.folium_map.get_root()
        folium_map_html = map_root.html.render()
        folium_map_script = map_root.script.render()

        return self._template.render(
            this=self,
            google_maps_url=google_maps_url,
            osm_url=osm_url,
            results=results,
            folium_map_html=folium_map_html,
            folium_map_script=folium_map_script,
        )

    def _calculate_results(self):
        if not self.fastest_path:
            return [["", 0, "NULL"]]
        results = [
            (
                "Fastest (red)",
                self.meters_to_feet(self.graph.path_length(self.fastest_path)),
                self.graph.compass_direction(self.fastest_path),
            )
        ]
        if self.shortest_path:
            results.append(
                (
                    "Shortest (yellow)",
                    self.meters_to_feet(self.graph.path_length(self.shortest_path)),
                    self.graph.compass_direction(self.shortest_path),
                )
            )
        return results

    @staticmethod
    def meters_to_feet(meters):
        """
        Convert the given distance in meters to feet.
        """
        return int(meters * 3.281)


@attr.s
class Page:
    """
    A full HTML page of interval calculations.
    """

    intervals = attr.ib(default=[])

    def add(self, interval):
        """
        Add an interval to the page for future rendering.
        """
        self.intervals.append(interval)

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
      {% for interval in this.intervals %}
      {% if loop.index > 1 %}<hr>{% endif %}
      {{ interval.render() }}
      {% endfor %}
    </body>
    </html>
    """
    )

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
	'--' AS IntervalType,
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
	CASE
		dh_type WHEN 1 THEN 'DH'
		WHEN 2 THEN 'PO'
		ELSE 'PI'
	END as IntervalType,
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


def parse_rows(rows):
    """
    Parse the given list of rows into a Page.
    """
    row_count = len(rows)
    stops = [
        (
            Stop(
                row["FromStopNumber"],
                row["FromStopDescription"],
                row["FromStopLatitude"],
                row["FromStopLongitude"],
            ),
            Stop(
                row["ToStopNumber"],
                row["ToStopDescription"],
                row["ToStopLatitude"],
                row["ToStopLongitude"],
            ),
        )
        for row in rows
    ]
    (from_stops, to_stops) = zip(*stops)
    graph = routing.RestrictedGraph.from_points(from_stops + to_stops)

    page = Page()

    for (index, (row, (from_stop, to_stop))) in enumerate(zip(rows, stops), 1):
        ox.utils.log(f"processing row {index} of {row_count}: {row!r}")
        interval = Interval.from_stops(
            from_stop, to_stop, graph, row["IntervalType"], row["IntervalDescription"]
        )
        page.add(interval)

    return page


def main(argv):
    """
    Entrypoint for the Missing Intervals Calculation.
    """
    ox.config(log_console=True)
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

    page = parse_rows(rows)
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

if __name__ == "__main__":
    main(parser.parse_args())
