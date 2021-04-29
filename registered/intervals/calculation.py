"""
Calculation of a fastest/shortest path for a given Interval.
"""
from typing import Optional, List
import attr
import osmnx as ox
from .routing import RestrictedGraph
from .interval import Stop, Interval, IntervalType

Path = List[int]


@attr.define(kw_only=True)
class IntervalCalculation:
    """
    One interval calculation.
    """

    interval: Interval
    fastest_path: Optional[Path] = attr.ib(default=None)
    shortest_path: Optional[Path] = attr.ib(default=None)

    @property
    def from_stop(self) -> Stop:
        "Return the from_stop of the Interval."
        return self.interval.from_stop

    @property
    def to_stop(self) -> Stop:
        "Return the to_stop of the Interval."
        return self.interval.to_stop

    @property
    def interval_type(self) -> str:
        "Return the formatted type of the Interval: Revenue, Deadhead, &c."
        return str(self.interval.type.name).title()

    @property
    def description(self) -> str:
        "Return the description of the Interval."
        return self.interval.description or ""

    @classmethod
    def calculate(
        cls, interval: Interval, graph: RestrictedGraph
    ) -> "IntervalCalculation":
        """
        Calculate the fastest/shortest paths, given an Interval.
        """
        fastest_path = shortest_path = None
        if should_calculate(interval):
            ox.utils.log(
                f"calculating interval from {interval.from_stop} to {interval.to_stop}"
            )
            fastest_path = graph.shortest_path(interval.from_stop, interval.to_stop)
            if fastest_path is not None:
                shortest_path = graph.shortest_path(
                    interval.from_stop, interval.to_stop, weight="length"
                )

        if fastest_path == shortest_path:
            shortest_path = None

        return cls(
            interval=interval,
            fastest_path=fastest_path,
            shortest_path=shortest_path,
        )

    def paths(self) -> List[Path]:
        """
        Return the list of unique paths in this calculation.
        """
        return [
            path for path in [self.fastest_path, self.shortest_path] if path is not None
        ]


def should_calculate(interval: Interval) -> bool:
    """
    Return True if we should calculate a path for the given Interval.

    - do not calculate Revenue intervals
    """
    return interval.type != IntervalType.REVENUE
