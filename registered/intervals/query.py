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
  (CASE
        WHEN gn1.use_survey = 1 THEN gn1.latitude
        ELSE gn1.map_latitude END) / 10000000
  as FromStopLatitude,
  (CASE
        WHEN gn1.use_survey = 1 THEN gn1.longitude
        ELSE gn1.map_longitude END) / 10000000
  as FromStopLongitude,
  gn2.geo_node_abbr AS ToStopNumber,
  gn2.geo_node_name AS ToStopDescription,
  (CASE
        WHEN gn2.use_survey = 1 THEN gn2.latitude
        ELSE gn2.map_latitude END) / 10000000
  as ToStopLatitude,
  (CASE
        WHEN gn2.use_survey = 1 THEN gn2.longitude
        ELSE gn2.map_longitude END) / 10000000
  as ToStopLongitude,
  MIN(RTRIM(r.route_abbr)) AS Route,
  MIN(RTRIM(rd.route_direction_name)) AS Direction,
  MIN(RTRIM(p.pattern_abbr)) AS Pattern,
  gni.distance_between_map AS DistanceBetweenMap,
  gni.distance_between_measured AS DistanceBetweenMeasured,
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
         gni.use_map,
         gn1.geo_node_abbr,
         gn1.geo_node_name,
         gn1.use_survey,
         gn1.latitude,
         gn1.map_latitude,
         gn1.longitude,
         gn1.map_longitude,
         gn2.geo_node_abbr,
         gn2.geo_node_name,
         gn2.use_survey,
         gn2.latitude,
         gn2.map_latitude,
         gn2.longitude,
         gn2.map_longitude
UNION
SELECT
  @ttvid + 0.2 AS RouteVersionId,
  gni.interval_id AS IntervalId,
  dh.dh_type AS IntervalType,
  gn1.geo_node_abbr AS FromStopNumber,
  gn1.geo_node_name AS FromStopDescription,
  (CASE
        WHEN gn1.use_survey = 1 THEN gn1.latitude
        ELSE gn1.map_latitude END) / 10000000
  as FromStopLatitude,
  (CASE
        WHEN gn1.use_survey = 1 THEN gn1.longitude
        ELSE gn1.map_longitude END) / 10000000
  as FromStopLongitude,
  gn2.geo_node_abbr AS ToStopNumber,
  gn2.geo_node_name AS ToStopDescription,
  (CASE
        WHEN gn2.use_survey = 1 THEN gn2.latitude
        ELSE gn2.map_latitude END) / 10000000
  as ToStopLatitude,
  (CASE
        WHEN gn2.use_survey = 1 THEN gn2.longitude
        ELSE gn2.map_longitude END) / 10000000
  as ToStopLongitude,
  MIN(RTRIM(r.route_abbr)) AS Route,
  MIN(RTRIM(rd.route_direction_name)) AS Direction,
  MIN(RTRIM(p.pattern_abbr)) AS Pattern,
  gni.distance_between_map AS DistanceBetweenMap,
  gni.distance_between_measured AS DistanceBetweenMeasured,
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
         gni.use_map,
         dh.dh_type,
         gn1.geo_node_abbr,
         gn1.geo_node_name,
         gn1.use_survey,
         gn1.latitude,
         gn1.map_latitude,
         gn1.longitude,
         gn1.map_longitude,
         gn2.geo_node_abbr,
         gn2.geo_node_name,
         gn2.use_survey,
         gn2.latitude,
         gn2.map_latitude,
         gn2.longitude,
         gn2.map_longitude
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
    formatted = SQL.format(where=where)
    if parameters is None:
        return formatted

    return (formatted, parameters + parameters)
