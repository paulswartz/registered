from itertools import product
from registered import routing
import pytest
from pytest import approx
from shapely.geometry import Point
import networkx as nx
import osmnx as ox


# helpful things for debugging:
ox.config(log_console=True)  # enable console logging inside OSMnx
#
# add the below to a test case to write a map with the given path
# # graph.folium_map(bc_high_school, federal_st, [path]).save("map.html")


def assert_has_path(origin, dest, graph=None, weight="travel_time"):
    """
    Create a shortest path between origin and dest, and assert that it has non-zero length.
    """
    if graph is None:
        graph = routing.RestrictedGraph.from_points([origin, dest])
    path = graph.shortest_path(origin, dest, weight=weight)
    assert path is not None
    assert graph.path_length(path) > 0
    return (graph, path)


def test_no_left_turn():
    bc_high_school = Point(-71.04149, 42.31760)
    federal_st = Point(-71.056411, 42.355286)
    bad_node = 61403875  # left turn from morrisey onto day blvd
    bad_from_edge = 541034265
    bad_to_edge = 645350240

    (graph, path) = assert_has_path(bc_high_school, federal_st)

    assert graph.path_length(path) == approx(5732, abs=1)
    # first and last path entries are psuedo-nodes, snapped from the given
    # shortest-path points
    assert path[1] in [5845347051, 7718883175]
    assert path[-2] in [61340621, 7637468345, 1202432362]

    if bad_node in path:
        index = path.index(bad_node)
        previous_node = path[index - 1]
        next_node = path[index + 1]
        previous_edge = graph.graph.edges[previous_node, bad_node, 0]
        next_edge = graph.graph.edges[bad_node, next_node, 0]
        assert (
            previous_edge["osmid"] != bad_from_edge
            and next_edge["osmid"] != bad_to_edge
        ), f"bad turn, coming from {previous_node} going to {next_node}"


class TestCompassDirection:
    ORIGINS = [
        (Point(-71.03991910663855, 42.33306759993236), None),
        (Point(-71.040217, 42.317071), None),
        (Point(-70.943385, 42.465441), None),
        (Point(-71.170956, 42.272991), None),
    ]
    DESTS = [
        (Point(-71.03599235273778, 42.335613467448354), None),
        (Point(-71.064371, 42.308101), "St Peters Sq @ Church"),
        (Point(-70.94593, 42.463623), "Washington St @ Munroe St"),
        (Point(-71.171963, 42.271777), "Charles River Loop"),
    ]
    DIRECTIONS = [88.7, 75.1, 125.4, 153.9]

    @pytest.mark.parametrize("origin,dest,compass", zip(ORIGINS, DESTS, DIRECTIONS))
    def test_compass_direction(self, origin, dest, compass):
        (origin, description) = origin
        if description is not None:
            setattr(origin, "description", description)

        (dest, description) = dest
        if description is not None:
            setattr(dest, "description", description)

        (graph, path) = assert_has_path(origin, dest)  # , graph=self.graph
        assert graph.compass_direction(path) == approx(compass)


class TestRouting:
    OD_PAIRS = [
        ((-71.084983, 42.39193), (-71.078666, 42.386049)),
        ((-70.99272, 42.418574), (-70.99205, 42.413385)),
        ((-71.101815, 42.436141), (-71.076315, 42.384167)),
        ((-71.1292, 42.39702), (-71.129116, 42.396704)),
        ((-71.129116, 42.396704), (-71.1292, 42.39702)),
        ((-70.94560, 42.46236), (-70.94726, 42.46206)),
    ]

    @pytest.mark.parametrize("pair", OD_PAIRS)
    def test_has_path(self, pair):
        (origin, dest) = pair
        origin_pt = Point(origin)
        dest_pt = Point(dest)
        (graph, _path) = assert_has_path(origin_pt, dest_pt, weight="travel_time")
        (_graph, path) = assert_has_path(
            origin_pt, dest_pt, graph=graph, weight="length"
        )


class TestMultiplePoints:
    ORIGINS = [(-71.03991910663855, 42.33306759993236), (-71.04149, 42.31760)]
    DESTS = [
        (-71.056411, 42.355286),
        (-71.03599235273778, 42.335613467448354),
    ]
    OD_PAIRS = list(product(ORIGINS, DESTS))

    @classmethod
    def setup_class(cls):
        points = [Point(point) for point in cls.ORIGINS + cls.DESTS]
        cls.graph = routing.RestrictedGraph.from_points(points)

    @pytest.mark.parametrize("pair", OD_PAIRS)
    def test_multiple_points(self, pair):
        (origin, dest) = pair
        origin_pt = Point(origin)
        dest_pt = Point(dest)
        (_graph, _path) = assert_has_path(origin_pt, dest_pt, graph=self.graph)


class TestFoliumMap:
    OD_PAIRS = [
        ((-71.084983, 42.39193), (-71.078666, 42.386049)),
        ((-70.894718, 42.254173), (-70.892174, 42.251347)),
    ]

    @pytest.mark.parametrize("pair", OD_PAIRS)
    def test_folium_map(self, pair):
        (origin, dest) = pair
        origin_pt = Point(origin)
        dest_pt = Point(dest)
        (graph, fast_path) = assert_has_path(origin_pt, dest_pt)
        (graph, short_path) = assert_has_path(origin_pt, dest_pt, graph=graph)
        folium_map = graph.folium_map(origin_pt, dest_pt, [fast_path, short_path])
        assert folium_map is not None
        assert folium_map._repr_html_()
