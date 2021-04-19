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

declare @ttvid numeric(9);
select @ttvid = max(time_table_version_id) from time_table_version;

select
	@ttvid + 0.2 as RouteVersionId,
    gni.interval_id as IntervalId,
	0 AS IntervalType,
	gn1.geo_node_abbr AS FromStopNumber,
	gn1.geo_node_name AS FromStopDescription,
	gn1.mdt_latitude/10000000 as FromStopLatitude,
	gn1.mdt_longitude/10000000 as FromStopLongitude,
	gn2.geo_node_abbr AS ToStopNumber,
	gn2.geo_node_name AS ToStopDescription,
	gn2.mdt_latitude/10000000 as ToStopLatitude,
	gn2.mdt_longitude/10000000 as ToStopLongitude,
	MIN(RTRIM(r.route_abbr)) as Route,
        MIN(RTRIM(rd.route_direction_name)) as Direction,
        MIN(RTRIM(p.pattern_abbr)) as Pattern,
    gni.DISTANCE_BETWEEN_MAP as DistanceBetweenMap,
    gni.DISTANCE_BETWEEN_MEASURED as DistanceBetweenMeasured,
    gni.COMPASS_DIRECTION as CompassDirection,
    CAST(gni.use_map AS INT) as UseMap
from
	pattern_geo_interval_xref pgix
inner join pattern p on
	pgix.pattern_id = p.pattern_id
inner join route r on
	p.route_id = r.route_id
inner join route_direction rd on
	p.route_direction_id = rd.route_direction_id
inner join geo_node_interval gni on
	pgix.geo_node_interval_id = gni.interval_id
inner join geo_node gn1 on
	gni.start_point_id = gn1.geo_node_id
inner join geo_node gn2 on
	gni.end_point_id = gn2.geo_node_id
where
	pgix.time_table_version_id = @ttvid
	AND ({where})
group by
    gni.interval_id,
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
select
	@ttvid + 0.2 as RouteVersionId,
    gni.interval_id as IntervalId,
    dh.DH_TYPE as IntervalType,
	gn1.geo_node_abbr AS FromStopNumber,
	gn1.geo_node_name AS FromStopDescription,
	gn1.mdt_latitude/10000000 as FromStopLatitude,
	gn1.mdt_longitude/10000000 as FromStopLongitude,
	gn2.geo_node_abbr AS ToStopNumber,
	gn2.geo_node_name AS ToStopDescription,
	gn2.mdt_latitude/10000000 as ToStopLatitude,
	gn2.mdt_longitude/10000000 as ToStopLongitude,
	MIN(RTRIM(r.route_abbr)) as Route,
        MIN(RTRIM(rd.route_direction_name)) as Direction,
        MIN(RTRIM(p.pattern_abbr)) as Pattern,
    gni.DISTANCE_BETWEEN_MAP as DistanceBetweenMap,
    gni.DISTANCE_BETWEEN_MEASURED as DistanceBetweenMeasured,
    gni.COMPASS_DIRECTION as CompassDirection,
    CAST(gni.use_map AS INT) as UseMap
from
	deadheads dh
inner join pattern p on
	dh.pattern_id = p.pattern_id
inner join route r on
	p.route_id = r.route_id
inner join route_direction rd on
	p.route_direction_id = rd.route_direction_id
inner join geo_node_interval gni on
	dh.geo_node_interval_id = gni.interval_id
inner join geo_node gn1 on
	gni.start_point_id = gn1.geo_node_id
inner join geo_node gn2 on
	gni.end_point_id = gn2.geo_node_id
where
	dh.time_table_version_id = @ttvid
    AND ({where})
group by
    gni.interval_id,
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
order by
	IntervalType,
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
