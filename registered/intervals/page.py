"""
Render shortest/fastest paths for intervals as HTML.
"""

from typing import Any, List, Optional, Tuple
import attr
import osmnx as ox
from jinja2 import Template
from .routing import RestrictedGraph
from .calculation import IntervalCalculation


@attr.define
class Page:
    """
    A full HTML page of interval calculations.
    """

    _graph: RestrictedGraph
    calculations: List[IntervalCalculation] = attr.ib(init=False, factory=list)

    def add(self, calculation: IntervalCalculation):
        """
        Add an interval to the page for future rendering.
        """
        self.calculations.append(calculation)  # pylint: disable=no-member

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
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{{ page.render_stop(this.from_stop) }}</td>
            <td>{{ page.render_stop(this.to_stop) }}</td>
          </tr>
        </tbody>
      </table>
      <table>
        <thead>
          <tr>
            <th>Interval Type</th>
            <th>Description</th>
            <th>Directions</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{{ this.interval_type}}</td>
            <td>{{ this.description }}</td>
            <td>
              {% if has_maps %}
              <a target="_blank"
                 href="{{ google_maps_url | e}}">Google Maps</a><br>
              <a target="_blank"
                 href="{{ osm_url | e}}">OpenStreetMap</a><br>
              {% endif %}
            </td>
          </tr>
        </tbody>
      </table>
      <table>
        <thead>
          <tr>
            <th>Route</th>
            <th>Length (ft)</th>
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
    {% if osm_url %}<a href="{{osm_url | e}}">OpenStreetMap</a><br>{% endif %}
    <a href="https://www.mbta.com/stops/{{ this.id }}">MBTA.com</a><br>
    <a href="https://api-v3.mbta.com/stops/{{ this.id }}">V3 API</a>
    """
    )

    def render_calculation(self, calculation: IntervalCalculation) -> str:
        """
        Render the calculation as HTML.
        """
        print(calculation)
        results = self._calculate_results(calculation)

        has_maps = calculation.is_located()
        if has_maps:
            google_maps_url = self._google_maps_url(
                calculation.from_stop, calculation.to_stop
            )
            osm_url = self._osm_url(calculation.from_stop, calculation.to_stop)
            folium_map = self._graph.folium_map(
                calculation.from_stop, calculation.to_stop, calculation.paths()
            )
            folium_map.render()
            map_root = folium_map.get_root()
            folium_map_html = map_root.html.render()
            folium_map_script = map_root.script.render()
        else:
            google_maps_url = osm_url = folium_map_html = folium_map_script = None

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
        results = []
        if calculation.interval.distance_between_measured:
            results.append(
                (
                    "Measured",
                    str(calculation.interval.distance_between_measured),
                )
            )
        if calculation.interval.distance_between_map:
            results.append(
                (
                    "Map",
                    str(calculation.interval.distance_between_map),
                )
            )
        named_paths = list(
            zip(["Fastest (red)", "Shortest (yellow)"], calculation.paths())
        )
        for name, path in named_paths:
            results.append(
                (
                    name,
                    str(self.meters_to_feet(self._graph.path_length(path))),
                )
            )
        if not named_paths:
            results.append(("Empty", "0"))
        return results

    @staticmethod
    def _google_maps_url(from_stop, to_stop):
        return (
            f"https://www.google.com/maps/dir/?api=1&"
            f"travelmode=driving&"
            f"origin={ from_stop.y },{ from_stop.x }&"
            f"destination={ to_stop.y },{ to_stop.x }"
        )

    @staticmethod
    def _osm_url(from_stop, to_stop) -> str:
        return (
            f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&"
            f"route={from_stop.y},{from_stop.x};{to_stop.y},{to_stop.x}"
        )

    @classmethod
    def render_stop(cls, stop) -> str:
        """
        Render a stop to HTML.
        """
        if hasattr(stop, "x") and hasattr(stop, "y"):
            osm_url = (
                f"https://www.openstreetmap.org/query?"
                f"lat={stop.y}&lon={stop.x}"
                f"#map=18/{stop.y}/{stop.x}"
            )
        else:
            osm_url = None
        return cls._stop_template.render(this=stop, osm_url=osm_url)

    @staticmethod
    def meters_to_feet(meters: float) -> int:
        """
        Convert the given distance in meters to feet.
        """
        return int(meters * 3.281)

    def render(self) -> str:
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


def null_str(value: Optional[Any]) -> str:
    """
    Return NULL if the value is None, otherwise str(value).
    """
    if value is None:
        return "NULL"

    return str(value)
