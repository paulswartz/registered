"""
Helper functions for the routing module.
"""

from shapely.geometry import Point, LineString
import osmnx as ox


def clean_width(width_str):
    """
    Clean width specifiers to a consistent number of meters.

    - "1" -> 1.0
    - "2.0 m" -> 2.0
    - "3;4" -> 7.0
    - "5.2 ft" -> 1.58496 (convert feet to meters)
    """
    FEET_TO_METERS = 0.3048  # pylint: disable=invalid-name

    if width_str in {"t", "none", "default", "below_default"}:
        return None

    try:
        return float(width_str)
    except ValueError:
        pass

    if ";" in width_str:
        return sum(clean_width(part) for part in width_str.split(";"))

    if width_str.endswith(" m"):
        return float(width_str[:-2])

    feet = None
    inches = None

    if width_str.endswith(" ft"):
        feet = width_str[:-3]

    elif width_str.endswith(" feet"):
        feet = width_str[:-5]

    elif width_str.endswith('"'):
        # feet and inches
        [feet, inches] = width_str[:-1].split("'")

    elif width_str.endswith("'"):
        feet = width_str[:-1]

    else:
        ox.utils.log(f"unknown width specification: {repr(width_str)}")
        return None

    feet = float(feet)
    if inches is not None:
        feet += float(inches) / 12

    return feet * FEET_TO_METERS


def ensure_set(value):
    """
    Given a single value or multiple values, ensure that we return a set.
    """
    if isinstance(value, int):
        return {value}

    return set(value)


def restrictions_in_polygon(polygon):
    """
    Fetch the turn restrictions inside the given polygon.

    Uses some internal OSMnx methods.
    """
    # pylint: disable=protected-access
    settings = ox.downloader._make_overpass_settings()
    restricted_nodes = set()
    restrictions = []
    for polygon_str in ox.downloader._make_overpass_polygon_coord_strs(polygon):
        query = (
            f"{settings};("
            f'relation["type"="restriction"]["restriction"~"no_"](poly:"{polygon_str}");'
            f");out;"
        )
        response = ox.downloader.overpass_request(data={"data": query})
        (new_nodes, new_restrictions) = osm_relations_to_restrictions(response)
        restricted_nodes |= new_nodes
        restrictions.extend(new_restrictions)
    return (restricted_nodes, restrictions)


def osm_relations_to_restrictions(response):
    """
    Turn an OSM relations query into two sets: "via" nodes, and (from, via, to) node triples.
    """
    ways = {}
    nodes = set()
    restrictions = []
    for element in response["elements"]:
        if element["type"] == "way":
            way_nodes = element["nodes"]
            ways[element["id"]] = way_nodes
        elif element["type"] == "relation":
            members = element["members"]
            node = [
                m["ref"] for m in members if m["role"] == "via" and m["type"] == "node"
            ]
            if len(node) != 1:
                # NB: does not handle "via" where it's a "way" not a "node"
                continue
            node = node[0]
            from_ways = {
                m["ref"] for m in members if m["role"] == "from" and m["type"] == "way"
            }
            to_ways = {
                m["ref"] for m in members if m["role"] == "to" and m["type"] == "way"
            }
            if not from_ways or not to_ways:
                continue
            nodes.add(node)
            restrictions.append((node, from_ways, to_ways))
    return (nodes, restrictions)


def angle_offset(base, angle):
    """
    Given a base bearing and a second bearing, return the offset in degrees.

    Positive offsets are clockwise/to the right, negative offsets are
    counter-clockwise/to the left.
    """
    # rotate the angle towards 0 by base
    offset = angle - base

    if offset <= -180:
        # bring it back into the (-180, 180] range
        return 360 + offset

    if offset > 180:
        return offset - 360

    return offset


def cut(line, distance):
    """
    Cuts a line in two at a distance from its starting point.
    """
    # from https://shapely.readthedocs.io/en/stable/manual.html
    coords = list(line.coords)
    if distance <= 0:
        distance = 0.01
    elif distance >= 1:
        distance = 0.99
    for i, coord in enumerate(coords):
        point_distance = line.project(Point(coord), normalized=True)
        if point_distance == distance:
            return [LineString(coords[: i + 1]), LineString(coords[i:])]
        if point_distance > distance:
            cut_point = line.interpolate(distance, normalized=True)
            return [
                LineString(coords[:i] + [(cut_point.x, cut_point.y)]),
                LineString([(cut_point.x, cut_point.y)] + coords[i:]),
            ]
    raise ValueError(f"unable to cut {line.wkt} at {distance}")
