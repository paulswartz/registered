from itertools import product
from registered.intervals import routing
import pytest
from pytest import approx
from shapely.geometry import Point
import networkx as nx
import osmnx as ox


def setup_module():
    """
    Setup for all tests in this module.
    """
    routing.configure_osmnx(log_console=True)


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


def test_no_storrow_drive():
    kenmore_busway = Point(-71.09583, 42.348927)
    mass_general = Point(-71.0692, 42.3609)
    (graph, path) = assert_has_path(kenmore_busway, mass_general)
    for from_node, to_node in zip(path, path[1:]):
        edge = graph.graph.edges[from_node, to_node, 0]
        if "name" not in edge:
            continue
        edge_name = edge["name"]
        assert edge_name != "Storrow Drive", f"from: {from_node}, to: {to_node}"


@pytest.mark.parametrize(
    "points",
    [
        [],
        [Point(0, 0)],
    ],
)
def test_empty_graph(points):
    with pytest.raises(routing.EmptyGraph):
        routing.RestrictedGraph.from_points(points)


def test_short_path():
    point = Point(-71.171963, 42.271777)
    graph = routing.RestrictedGraph.from_points([point])
    path = graph.shortest_path(Point(0, 0), Point(0, 0))
    assert len(path) == 1


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
