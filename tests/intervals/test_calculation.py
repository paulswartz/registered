from shapely.geometry import Point
from registered.intervals.interval import Stop, Interval
from registered.intervals.calculation import should_ignore_interval


def test_should_ignore_interval():
    point = Point(0, 0)
    sullivan_1 = Stop(
        point, id="29001", description="Sullivan Station Busway - Berth 1"
    )
    sullivan_2 = Stop(
        point, id="20002", description="Sullivan Station Busway - Berth 2"
    )
    fields_corner = Stop(point, id="323", description="Fields Corner Busway")
    chelsea_inbound = Stop(point, id="74630", description="Chelsea - Inbound")
    chelsea_outbound = Stop(point, id="74631", description="Chelsea - Outbound")

    assert should_ignore_interval(Interval(from_stop=sullivan_1, to_stop=sullivan_1))
    assert should_ignore_interval(Interval(from_stop=sullivan_1, to_stop=sullivan_2))
    assert (
        should_ignore_interval(Interval(from_stop=sullivan_1, to_stop=fields_corner))
        is False
    )
    assert should_ignore_interval(
        Interval(from_stop=chelsea_inbound, to_stop=chelsea_outbound)
    )
