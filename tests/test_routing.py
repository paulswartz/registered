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


@pytest.mark.parametrize(
    "base,angle,expected",
    [
        (0, 90, 90),
        (0, 180, 180),
        (0, 270, -90),
        (180, 0, 180),
        (180, 90, -90),
        (180, 180, 0),
        (180, 270, 90),
        (270, 0, 90),
        (270, 315, 45),
        (270, 225, -45),
        (359, 0, 1),
        (359, 358, -1),
        (190, 179, -11),
    ],
)
def test_angle_offset(base, angle, expected):
    assert routing.angle_offset(base, angle) == approx(expected)


def test_osm_relations_to_restrictions():
    response = {
        "elements": [
            {"type": "node", "id": 1},
            {"type": "node", "id": 2},
            {"type": "node", "id": 3},
            {"type": "node", "id": 4},
            {"type": "node", "id": 5},
            {"type": "way", "id": 6, "nodes": [1, 2, 3]},
            {"type": "way", "id": 7, "nodes": [2, 4, 5]},
            {
                "type": "relation",
                "id": 8,
                "members": [
                    {"type": "way", "ref": 6, "role": "from"},
                    {"type": "node", "ref": 2, "role": "via"},
                    {"type": "way", "ref": 7, "role": "to"},
                ],
            },
        ]
    }
    (nodes, restrictions) = routing.RestrictedGraph.osm_relations_to_restrictions(
        response
    )
    assert set(nodes) == {2}
    assert restrictions == [(2, {6}, {7})]


def test_osm_relations_to_restrictions_same_way_uturn():
    response = {
        "elements": [
            {"type": "node", "id": 1},
            {"type": "node", "id": 2},
            {"type": "node", "id": 3},
            {"type": "way", "id": 4, "nodes": [1, 2, 3]},
            {
                "type": "relation",
                "id": 5,
                "members": [
                    {"type": "way", "ref": 4, "role": "from"},
                    {"type": "node", "ref": 3, "role": "via"},
                    {"type": "way", "ref": 4, "role": "to"},
                ],
            },
        ]
    }
    (nodes, restrictions) = routing.RestrictedGraph.osm_relations_to_restrictions(
        response
    )
    assert set(nodes) == {3}
    assert restrictions == [(3, {4}, {4})]


@pytest.mark.parametrize(
    "width,actual",
    [
        ("1", 1.0),
        ("2.0 m", 2.0),
        ("3;4", 7.0),
        ("5.2 ft", 1.58496),
        ("4'6\"", 1.3716),
        ("14'", 4.2672),
        ("t", None),
    ],
)
def test_clean_width(width, actual):
    if actual is not None:
        actual = approx(actual)
    assert routing.RestrictedGraph.clean_width(width) == actual


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


def test_compass_direction():
    origin = Point(-71.03991910663855, 42.33306759993236)
    dest = Point(-71.03599235273778, 42.335613467448354)

    (graph, path) = assert_has_path(origin, dest)

    assert graph.compass_direction(path) == approx(88.7, abs=0.2)


def test_nearest_street_church_st():
    origin = Point(-71.040217, 42.317071)
    dest = Point(-71.064371, 42.308101)

    (graph, path) = assert_has_path(origin, dest)
    # if the compass direction is closer to 340, then the path has made the
    # turn onto Percival.
    assert graph.compass_direction(path) == approx(250, abs=1)


def test_nearest_street_washington():
    origin = Point(-70.943385, 42.465441)
    dest = Point(-70.94593, 42.463623)
    setattr(dest, "description", "Washington St @ Munroe St")

    (graph, path) = assert_has_path(origin, dest)
    # if the compass direction is closer to 45, then the path went around to
    # Munroe St
    assert graph.compass_direction(path) == approx(125, abs=1)


def test_folium_map():
    origin = Point(-71.03991910663855, 42.33306759993236)
    dest = Point(-71.03599235273778, 42.335613467448354)

    (graph, path) = assert_has_path(origin, dest)
    folium_map = graph.folium_map(origin, dest, [path])
    assert folium_map is not None
    assert folium_map._repr_html_()


def test_multiple_points():
    origins = [Point(-71.03991910663855, 42.33306759993236), Point(-71.04149, 42.31760)]
    dests = [
        Point(-71.056411, 42.355286),
        Point(-71.03599235273778, 42.335613467448354),
    ]
    graph = None

    for (origin, dest) in product(origins, dests):
        (graph, _path) = assert_has_path(origin, dest, graph=graph)


class TestRouting:
    OD_PAIRS = [
        ((-71.084983, 42.39193), (-71.078666, 42.386049)),
        ((-70.99272, 42.418574), (-70.99205, 42.413385)),
        ((-71.101815, 42.436141), (-71.076315, 42.384167)),
    ]

    def setup_class(self):
        points = [Point(p) for points in self.OD_PAIRS for p in points]
        self.graph = routing.RestrictedGraph.from_points(points)

    @pytest.mark.parametrize("weight", ["length", "travel_time"])
    @pytest.mark.parametrize("origin,dest", OD_PAIRS)
    def test_has_path(self, weight, origin, dest):
        origin_pt = Point(origin)
        dest_pt = Point(dest)
        (_graph, path) = assert_has_path(
            origin_pt, dest_pt, graph=self.graph, weight=weight
        )
        print(path)
