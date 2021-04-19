"""
Generate a SQL query for returning intervals.
"""
from typing import Optional, Sequence, Any, Union, Tuple, Dict
from registered import db

Parameters = Sequence[Any]


def read_database(
    where: str, parameters: Optional[Parameters] = None
) -> Dict[str, Any]:
    """
    Read intervals from the TransitMaster DB, given a WHERE query and optionally parameters.
    """
    conn = db.conn()
    cursor = conn.cursor()
    if parameters is None:
        cursor.execute(sql(where))
    else:
        cursor.execute(*sql(where, parameters))

    sql_headers = [desc[0] for desc in cursor.description]
    result = cursor.fetchall()
    return [dict(zip(sql_headers, row)) for row in result]


SQL = """
SET NOCOUNT ON;

DECLARE @ttvid numeric(9);
SELECT
  @ttvid = MAX(time_table_version_id)
FROM time_table_version;

SELECT
  @ttvid + 0.2 AS RouteVersionId,
  gni.interval_id AS IntervalId,
  0 AS IntervalType,
  gn1.geo_node_abbr AS FromStopNumber,
  gn1.geo_node_name AS FromStopDescription,
  gn1.mdt_latitude / 10000000 AS FromStopLatitude,
  gn1.mdt_longitude / 10000000 AS FromStopLongitude,
  gn2.geo_node_abbr AS ToStopNumber,
  gn2.geo_node_name AS ToStopDescription,
  gn2.mdt_latitude / 10000000 AS ToStopLatitude,
  gn2.mdt_longitude / 10000000 AS ToStopLongitude,
  MIN(RTRIM(r.route_abbr)) AS Route,
  MIN(RTRIM(rd.route_direction_name)) AS Direction,
  MIN(RTRIM(p.pattern_abbr)) AS Pattern,
  gni.distance_between_map AS DistanceBetweenMap,
  gni.distance_between_measured AS DistanceBetweenMeasured,
  gni.compass_direction AS CompassDirection,
  CAST(gni.use_map AS int) AS UseMap
FROM pattern_geo_interval_xref pgix
INNER JOIN pattern p
  ON pgix.pattern_id = p.pattern_id
INNER JOIN route r
  ON p.route_id = r.route_id
INNER JOIN route_direction rd
  ON p.route_direction_id = rd.route_direction_id
INNER JOIN geo_node_interval gni
  ON pgix.geo_node_interval_id = gni.interval_id
INNER JOIN geo_node gn1
  ON gni.start_point_id = gn1.geo_node_id
INNER JOIN geo_node gn2
  ON gni.end_point_id = gn2.geo_node_id
WHERE pgix.time_table_version_id = @ttvid
AND ({where})
GROUP BY gni.interval_id,
         gni.distance_between_map,
         gni.distance_between_measured,
         gni.compass_direction,
         gni.use_map,
         gn1.geo_node_abbr,
         gn1.geo_node_name,
         gn1.mdt_latitude,
         gn1.mdt_longitude,
         gn2.geo_node_abbr,
         gn2.geo_node_name,
         gn2.mdt_latitude,
         gn2.mdt_longitude
UNION
SELECT
  @ttvid + 0.2 AS RouteVersionId,
  gni.interval_id AS IntervalId,
  dh.dh_type AS IntervalType,
  gn1.geo_node_abbr AS FromStopNumber,
  gn1.geo_node_name AS FromStopDescription,
  gn1.mdt_latitude / 10000000 AS FromStopLatitude,
  gn1.mdt_longitude / 10000000 AS FromStopLongitude,
  gn2.geo_node_abbr AS ToStopNumber,
  gn2.geo_node_name AS ToStopDescription,
  gn2.mdt_latitude / 10000000 AS ToStopLatitude,
  gn2.mdt_longitude / 10000000 AS ToStopLongitude,
  MIN(RTRIM(r.route_abbr)) AS Route,
  MIN(RTRIM(rd.route_direction_name)) AS Direction,
  MIN(RTRIM(p.pattern_abbr)) AS Pattern,
  gni.distance_between_map AS DistanceBetweenMap,
  gni.distance_between_measured AS DistanceBetweenMeasured,
  gni.compass_direction AS CompassDirection,
  CAST(gni.use_map AS int) AS UseMap
FROM deadheads dh
INNER JOIN pattern p
  ON dh.pattern_id = p.pattern_id
INNER JOIN route r
  ON p.route_id = r.route_id
INNER JOIN route_direction rd
  ON p.route_direction_id = rd.route_direction_id
INNER JOIN geo_node_interval gni
  ON dh.geo_node_interval_id = gni.interval_id
INNER JOIN geo_node gn1
  ON gni.start_point_id = gn1.geo_node_id
INNER JOIN geo_node gn2
  ON gni.end_point_id = gn2.geo_node_id
WHERE dh.time_table_version_id = @ttvid
AND ({where})
GROUP BY gni.interval_id,
         gni.distance_between_map,
         gni.distance_between_measured,
         gni.compass_direction,
         gni.use_map,
         dh.dh_type,
         gn1.geo_node_abbr,
         gn1.geo_node_name,
         gn1.mdt_latitude,
         gn1.mdt_longitude,
         gn2.geo_node_abbr,
         gn2.geo_node_name,
         gn2.mdt_latitude,
         gn2.mdt_longitude
ORDER BY IntervalType,
Route,
Direction,
Pattern;
"""


def sql(
    where: str, parameters: Optional[Parameters] = None
) -> Union[str, Tuple[str, Parameters]]:
    """
    Return a SQL query, usable for querying the TransitMaster database.

    If provided, parameters are returned duplicated, to account for the face that the WHERE clause
    is also duplicated.
    """
    sql = SQL.format(where=where)
    if parameters is None:
        return sql

    return (sql, parameters + parameters)
