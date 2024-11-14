"""
Calculate shortest/fastest paths for missing intervals.
"""

from difflib import SequenceMatcher
from itertools import count
import os
import sys
import attr
import folium
import osmnx as ox
import pandas as pd
import rtree
import shapely
from shapely.geometry import MultiPoint, box
import networkx as nx
from .routing_helpers import (
    clean_width,
    ensure_set,
    restrictions_in_polygon,
    angle_offset,
    cut,
)

DEFAULT_COLORS = ["red", "yellow", "blue", "green"]
USEFUL_NODE_TAGS = []
USEFUL_WAY_TAGS = [
    "oneway",
    "name",
    "highway",
    "maxspeed",
    "service",
    "access",
    "width",
    "maxheight",
    "hgv",
]


def configure_osmnx(**kwargs):
    """
    Set configuration for OSMNX.
    """
    ox.settings.cache_folder = os.environ.get("OSMNX_CACHE_DIR", "./cache")
    ox.settings.useful_tags_node = USEFUL_NODE_TAGS
    ox.settings.useful_tags_way = USEFUL_WAY_TAGS

    for k, v in kwargs.items():
        setattr(ox.settings, k, v)


class EmptyGraph(Exception):
    """
    Raised if the graph does not have any data.
    """


class NodesCache:
    """
    Cache of the nodes Frame.

    Currently only used to generate a known-unique ID for a new node.
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, gdf):
        self.counter = count(gdf.index.max() + 1)

    def new_id(self):
        """
        Return a new ID to use for a newly-created node.
        """
        return next(self.counter)


class EdgesCache:
    """
    Cache of the edges GeoDataFrame, with some helpful methods for querying/updating.
    """

    def __init__(self, gdf):
        self.gdf = gdf
        self.counter = count()
        capacity = int(len(gdf) * 1.1)
        props = rtree.index.Property(
            index_capacity=capacity,
            dimension=2,
            variant=rtree.index.RT_Star,
            fill_factor=0.9,
        )
        self.index = rtree.index.Index(
            (
                (next(self.counter), t.geometry.bounds, t.Index)
                for t in gdf.itertuples()
            ),
            properties=props,
        )

    def nearest_edges(self, point):
        """
        Return the nearest edges to the given point.

        If more than one edge is closest (and they aren't service roads),
        returns the one where the point is on the right (not left) side.
        """
        # get a few nearest edges to test, then get the actual closest one
        nearest = self.gdf.loc[self.index.nearest(point.bounds, 4, objects="raw")]
        distances = nearest["geometry"].map(point.distance, na_action="ignore")
        # bias against starting on a motorway
        distances.loc[nearest.highway.str.startswith("motorway")] *= 3
        if hasattr(point, "description"):
            # bias the distance towards more similar names. this helps put
            # the point on the right edge, given a description like
            # "Washington St @ Blah St".
            name_ratio = nearest["name"].map(
                lambda x: SequenceMatcher(None, point.description, x).ratio(),
                na_action="ignore",
            )
            if name_ratio.notna().any():
                name_ratio = name_ratio.fillna(name_ratio.mean())
                distances = distances / name_ratio
        min_distance = distances.min() + 1e-6
        within_distance = nearest.loc[distances <= min_distance]

        if len(within_distance) < 2:
            # only one closest edge, return it
            return within_distance

        if within_distance["highway"].eq("service").all():
            # all edges are service roads, so allow going either direction
            return within_distance

        # otherwise, find which of the multiple edges has the point on the
        # right-hand side.
        def calc_angle(row):
            # might need to be updated if we stare simplifying the graph. in
            # that case, we'd need to find the bearing at the projection of
            # point on the given geometry. -ps
            (tail_x, tail_y) = row["geometry"].coords[0]
            angle_bearing = ox.bearing.calculate_bearing(
                tail_y, tail_x, point.y, point.x
            )
            return angle_offset(row["bearing"], angle_bearing)

        offset = within_distance.apply(calc_angle, axis=1)
        # offsets >0 are on the right-hand side
        idx = offset.idxmax()
        return within_distance.loc[[idx]]

    def geometry(self, from_node, to_node=None):
        """
        Return the geometry for the given from/to edge.
        """
        if to_node is None:
            edge = from_node
        else:
            edge = (from_node, to_node, 0)
        return self.gdf.loc[edge, "geometry"]

    def update(self, graph):
        """
        Update the cache with the new edges from the given graph.
        """
        gdf = ox.convert.graph_to_gdfs(graph, nodes=False)
        gdf = gdf.loc[~gdf.index.isin(self.gdf.index)]
        self.gdf = pd.concat([self.gdf, gdf])
        self.gdf.sort_index(inplace=True)
        for edge in gdf.itertuples():
            self.index.insert(next(self.counter), edge.geometry.bounds, edge.Index)


@attr.s(repr=False)
class RestrictedGraph:
    """
    Model a OSM street graph with turn restrictions.

    - `graph`: a `nx.MultiDiGraph` representing the primitive graph
    - `restricted_nodes`: a Set of node IDs which have a turn restriction
    - `restrictions`: a List of (v, {from_osmids}, {to_osmids}) triples which
      represent invalid turns
    """

    graph = attr.ib()
    restricted_nodes = attr.ib(factory=set)
    restrictions = attr.ib(factory=list)

    def __attrs_post_init__(self):
        # pylint: disable=attribute-defined-outside-init
        (nodes, edges) = ox.convert.graph_to_gdfs(self.graph)
        self._nodes_cache = NodesCache(nodes)
        self._edges_cache = EdgesCache(edges)
        self._created_nodes = {}

    def shortest_path(self, from_point, to_point, weight="travel_time"):
        """
        Calculate the shortest path from/to given lat/lon pairs.

        The shortest path is either by travel time (default) or by length (weight="length").
        """
        orig = self.closest_node(from_point)
        dest = self.closest_node(to_point)

        try:
            (_length, path) = nx.shortest_path_with_turn_restrictions(
                self.graph, orig, dest, self.restricted, weight=weight
            )
        except nx.NetworkXNoPath:
            return None

        return path

    def closest_node(self, point):
        """
        Return the ID of the closest node to the given Point.

        If there isn't an existing node that's close, find the nearest edges
        and split them at the given point, returning the new node ID.
        """
        if point.wkb in self._created_nodes:
            return self._created_nodes[point.wkb]

        ox.utils.log(f"finding closest edge to {point.wkt}")
        nearest_edges = self._edges_cache.nearest_edges(point)
        snapped_point = shapely.ops.nearest_points(
            nearest_edges.iloc[0].geometry, point
        )[0]

        ox.utils.log(f"snapping {point.wkt} to {snapped_point.wkt}")
        name = self._nodes_cache.new_id()
        ox.utils.log(f"creating new node {name}")
        for nearest_edge in nearest_edges.index:
            self.split_edge_at_point(nearest_edge, name, snapped_point)

        self._created_nodes[point.wkb] = name
        return name

    def split_edge_at_point(self, edge, name, point):
        """
        Given an edge, the new node ID, and a Point, split the given edge in two at Point.
        """
        # 1. create a new node at point
        # 2. delete the old edge
        # 3. create two new edges, from head to node, and node to tail
        ox.utils.log(f"splitting {edge} at {point.wkt}")
        (head, tail) = edge[:2]
        edge_attrs = self.graph.edges[edge].copy()
        ox.utils.log(f"edge OSM ID(s): {edge_attrs['osmid']}")
        length = edge_attrs.pop("length")
        del edge_attrs["travel_time"]
        # simple edges don't have a geometry in the graph, only in the cache
        edge_attrs.pop("geometry", None)
        geometry = self._edges_cache.geometry(edge)
        head_percent = geometry.project(point, normalized=True)
        [head_geometry, tail_geometry] = cut(geometry, head_percent)

        subgraph = nx.MultiDiGraph(crs=self.graph.graph["crs"])
        subgraph.add_node(name, y=point.y, x=point.x, geometry=point)
        subgraph.add_node(head, **self.graph.nodes[head])
        subgraph.add_node(tail, **self.graph.nodes[tail])
        subgraph.add_edge(
            head,
            name,
            **edge_attrs,
            length=length * head_percent,
            geometry=head_geometry,
        )
        subgraph.add_edge(
            name,
            tail,
            **edge_attrs,
            length=length * (1 - head_percent),
            geometry=tail_geometry,
        )

        return self.update(subgraph, name)

    def update(self, subgraph, name):
        """
        Updates the current RestrictedGraph with a new node (name) and edges.

        Also updates the caches.
        """

        subgraph = self.add_graph_features(subgraph)

        self.graph.update(subgraph)
        self._edges_cache.update(subgraph)

        return name

    def path_length(self, path):
        """
        Returns the length (in meters) of the given path.
        """
        gdf = ox.routing.route_to_gdf(self.graph, path, weight="length")
        return gdf["length"].sum()

    def folium_map(self, from_point, to_point, paths, **kwargs):
        """
        Create a `folium.Map` with the given from/to points, and optionally some paths.

        Returns the map.
        """
        route_map = folium.Map(
            tiles="https://cdn.mbta.com/osm_tiles/{z}/{x}/{y}.png",
            attr="&copy; <a href='http://osm.org/copyright'>OpenStreetMap</a> contributors",
            zoom_start=1,
            **kwargs,
        )

        for path, color in zip(paths, DEFAULT_COLORS):
            locations = [
                (row[1], row[0])
                for (from_node, to_node) in zip(path, path[1:])
                for row in self._edges_cache.geometry(from_node, to_node).coords
            ]
            folium.PolyLine(locations, weight=2, color=color).add_to(route_map)

        folium.Marker(
            (from_point.y, from_point.x), icon=folium.Icon(icon="play", color="green")
        ).add_to(route_map)
        folium.Marker(
            (to_point.y, to_point.x), icon=folium.Icon(icon="stop", color="red")
        ).add_to(route_map)

        [east, north, west, south] = MultiPoint([from_point, to_point]).bounds
        route_map.fit_bounds([(north, east), (south, west)])

        return route_map

    QUERIES = {
        # This Overpass API query gets private access roads which don't block
        # public service vehicles (PSVs) aka buses.
        "drive_service": {"network_type": "drive_service"},
        "PSV": {"custom_filter": '["highway"]["access"="private"]["psv"!~"no"]'},
        "parking": {"custom_filter": '["highway"]["service"~"parking|parking_aisle"]'},
    }

    @classmethod
    def from_points(cls, points):
        """
        Create a RestrictedGraph covering a list of (lat, lon) points.

        The polygon covering all the points is generated by finding the
        bounding box for the points, then querying the OSM API for that box.
        """
        # pylint: disable=protected-access
        if not points:
            raise EmptyGraph("unable to build graph with no points")
        [xmin, ymin, xmax, ymax] = MultiPoint(list(points)).buffer(0.02).bounds
        polygon = box(xmin, ymin, xmax, ymax)
        graph = nx.MultiDiGraph()
        for name, kwargs in cls.QUERIES.items():
            try:
                ox.utils.log(f"fetching {name} graph")
                extra_graph = ox.graph_from_polygon(
                    polygon,
                    retain_all=True,
                    simplify=False,
                    truncate_by_edge=False,
                    **kwargs,
                )
            except ox._errors.InsufficientResponseError:
                pass
            else:
                graph.update(extra_graph)

        if len(graph) == 0:
            raise EmptyGraph(f"unable to build graph from {polygon.wkt}")

        ox.utils.log("fetching restrictions")
        (restricted_nodes, restrictions) = restrictions_in_polygon(polygon)
        # simplification disabled for now; causes a test failure -ps
        # graph = ox.simplification.simplify_graph(graph)
        ox.utils.log("adding graph features")
        graph = cls.add_graph_features(graph)

        return cls(
            graph=graph, restricted_nodes=restricted_nodes, restrictions=restrictions
        )

    @classmethod
    def add_graph_features(cls, graph):
        """
        Update the given graph with important features.

        - width in meters
        - speeds in km/h
        - travel times
        - bearings in degrees
        """
        graph = cls.add_widths(graph)

        # impute speed on all edges missing data
        graph = ox.add_edge_speeds(
            graph,
            hwy_speeds={
                "motorway": 90,
                "trunk": 90,
                "trunk_link": 60,
                "primary": 60,
                "secondary": 50,
                "tertiary": 30,
                "private": 16,
                "service": 16,
                "residential": 16,
            },
        )
        # calculate travel time (seconds) for all edges
        graph = ox.add_edge_travel_times(graph)

        # penalize some types of edges
        graph = cls.add_edge_penalties(graph)

        # add edge bearings
        graph = ox.add_edge_bearings(graph)

        return graph

    @staticmethod
    def add_widths(graph):
        """
        Add "width_m" and "maxheight_m" to each edge with a width value, normalizing it to meters.
        """
        widths = nx.get_edge_attributes(graph, "width")
        widths_m = {k: clean_width(v) for (k, v) in widths.items()}
        nx.set_edge_attributes(graph, values=widths_m, name="width_m")

        maxheights = nx.get_edge_attributes(graph, "maxheight")
        maxheights_m = {k: clean_width(v) for (k, v) in maxheights.items()}
        nx.set_edge_attributes(graph, values=maxheights_m, name="maxheight_m")

        return graph

    @classmethod
    def add_edge_penalties(cls, graph):
        """
        Penalize some edges to reduce their use in routing.
        """
        edges = ox.convert.graph_to_gdfs(graph, nodes=False, fill_edge_geometry=False)
        key = ["travel_time", "length"]

        # penalize residential streets
        residential = edges["highway"].eq("residential")
        edges.loc[residential, key] *= 1.5

        # penalize narrow streets
        if "width_m" in edges.columns:
            narrow = edges["width_m"] < 5
            edges.loc[narrow, key] *= 1.5

        # heavily penalize edges with a height limit
        if "maxheight_m" in edges.columns:
            bus_height = 3.7  # ~12ft
            edges.loc[edges["maxheight_m"] < bus_height, ["travel_time", "length"]] = (
                sys.float_info.max
            )

        # penalize edges which don't allow heavy vehicles
        if "hgv" in edges.columns:
            hgv_no = edges["hgv"].eq("no")
            edges.loc[hgv_no, key] = sys.float_info.max

        nx.set_edge_attributes(graph, values=edges["travel_time"], name="travel_time")
        nx.set_edge_attributes(graph, values=edges["length"], name="length")
        return graph

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def restricted(self, origin, turn, dest, from_attrs, to_attrs):
        """
        Return a boolean indicating if the given turn is restricted.

        A turn is restricted if there is a `via` relation of `type`
        `restriction` and a `restriction` starting with `no_` (like
        `no_left_turn` or `no_uturn`)

        It is also restricted if the first and last nodes are the same (a
        U-turn).
        """
        if origin == dest:
            # avoid u-turns
            return True
        from_bearing = from_attrs.get("bearing")
        to_bearing = to_attrs.get("bearing")
        offset = angle_offset(from_bearing, to_bearing)
        if abs(offset) > 135:
            # avoid making U-ish turns
            return True

        if turn not in self.restricted_nodes:
            return False
        from_ways = ensure_set(from_attrs["osmid"])
        to_ways = ensure_set(to_attrs["osmid"])

        for node, invalid_from, invalid_to in self.restrictions:
            if node != turn:
                continue
            if (invalid_from & from_ways) and (invalid_to & to_ways):
                return True
        return False
