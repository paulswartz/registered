from shapely.geometry import Point
from registered.intervals.routing import RestrictedGraph
from registered.intervals.interval import Stop, Interval, IntervalType
from registered.intervals.calculation import IntervalCalculation


class TestIntervalCalculation:
    def test_does_not_calculate_revenue_interval(self):
        nubian_station = Stop(
            Point(-70.99272, 42.418574),
            id="5774",
            description="Revere St @ Sagamore St",
        )
        washington_st = Stop(
            Point(-70.99205, 42.413385),
            id="15795",
            description="Wonderland Busway",
        )
        interval = Interval(
            type=IntervalType.REVENUE, from_stop=nubian_station, to_stop=washington_st
        )
        graph = RestrictedGraph.from_points([nubian_station.point, washington_st.point])
        calculation = IntervalCalculation.calculate(interval, graph)
        assert calculation.paths() == []
