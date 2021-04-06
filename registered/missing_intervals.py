"""
Calculate shortest/fastest paths for missing intervals.
"""
import csv
import re
import sys
import attr
import osmnx as ox
import requests
from jinja2 import Template
from shapely.geometry import Point
import networkx as nx
from registered import routing

GARAGE_LOCATIONS = {
    "fell": Point(-71.08891, 42.42174),
    "censq": Point(-70.945598, 42.46236),
    "ncamb": Point(-71.12895, 42.3971),
}


def points_from_stop_ids(stop_ids):
    """
    Finds Points for the given stop IDs.

    Returns a dictionary mapping the stop ID to the Point.
    """
    garages = {
        garage: point
        for (garage, point) in GARAGE_LOCATIONS.items()
        if garage in stop_ids
    }
    params = {
        "filter[id]": ",".join(str(i) for i in stop_ids),
        "fields[stop]": "latitude,longitude",
    }

    req = requests.get("https://api-v3.mbta.com/stops/", params=params)

    return {
        j["id"]: Point(j["attributes"]["longitude"], j["attributes"]["latitude"])
        for j in req.json()["data"]
    } | garages


class Stop(Point):  # pylint: disable=too-few-public-methods
    """
    A location to calculate an interval (either from or to).
    """

    def __init__(self, id, description, point):  # pylint: disable=redefined-builtin
        """
        Initialize our Stop with the extra parameters.
        """
        Point.__init__(self, point)
        self.id = id  # pylint: disable=invalid-name
        self.description = description

    _template = Template(
        """
    {{ this.description }} ({{ this.id }})<br>
    <a href="{{osm_url | e}}">OpenStreetMap</a>
    """
    )

    def __repr__(self):
        return f"Stop(id={repr(self.id)}, description={repr(self.description)}, point={self.wkt})"

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
        folium_map.render()

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
            return []
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


def parse_csv(input_io):
    """
    Parse the CSV data in into a Page.
    """
    rows = list(csv.DictReader(input_io))

    return parse_rows(rows)


def parse_rows(rows):
    """
    Parse the given iterable of rows into a Page.
    """
    row_count = len(rows)
    stop_ids = {
        stop_id
        for row in rows
        for stop_id in [row["FromStopNumber"], row["ToStopNumber"]]
    }
    stop_locations = points_from_stop_ids(stop_ids)
    missing_stops = {stop_id for stop_id in stop_ids if stop_id not in stop_locations}
    if missing_stops:
        raise KeyError(f"unable to find locations for {missing_stops}")
    graph = routing.RestrictedGraph.from_points(stop_locations.values())

    page = Page()

    for (index, row) in enumerate(rows, 1):
        ox.utils.log(f"processing row {index} of {row_count}: {repr(row)}")
        from_stop = Stop(
            row["FromStopNumber"],
            row["FromStopDescription"],
            stop_locations[row["FromStopNumber"]],
        )
        to_stop = Stop(
            row["ToStopNumber"],
            row["ToStopDescription"],
            stop_locations[row["ToStopNumber"]],
        )
        interval = Interval.from_stops(
            from_stop, to_stop, graph, row["IntervalType"], row["IntervalDescription"]
        )
        page.add(interval)

    return page


def main(argv):
    """
    Entrypoint for the Missing Intervals Calculation.
    """
    if len(argv) == 1:
        # stdin -> stdout
        page = parse_csv(sys.stdin)
        sys.stdout.write(page.render())

    elif len(argv) == 2:
        # file -> stdout
        with open(argv[1]) as input_io:
            page = parse_csv(input_io)
            sys.stdout.write(page.render())

    elif len(argv) == 3:
        with open(argv[1]) as input_io:
            with open(argv[2], "w") as out_io:
                ox.config(log_console=True)
                page = parse_csv(input_io)
                out_io.write(page.render())

    else:
        raise RuntimeError("expected 0, 1, or 2 command line arguments")


if __name__ == "__main__":
    main(sys.argv)
