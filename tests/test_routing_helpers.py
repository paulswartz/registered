from itertools import product
from registered.routing_helpers import *
import pytest
from pytest import approx
from shapely.geometry import Point
import networkx as nx
import osmnx as ox


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
    assert angle_offset(base, angle) == approx(expected)


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
    (nodes, restrictions) = osm_relations_to_restrictions(response)
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
    (nodes, restrictions) = osm_relations_to_restrictions(response)
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
    assert clean_width(width) == actual
