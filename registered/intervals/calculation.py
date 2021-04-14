"""
Calculation of a fastest/shortest path for a given Interval.
"""
import re
from typing import Optional, List
import attr
import osmnx as ox
from .routing import RestrictedGraph
from .interval import Stop, Interval

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
        return self.interval.from_stop

    @property
    def to_stop(self) -> Stop:
        return self.interval.to_stop

    @property
    def interval_type(self) -> str:
        return str(self.interval.type).title()

    @property
    def description(self) -> str:
        return self.interval.description or ""

    @classmethod
    def calculate(
        cls, interval: Interval, graph: RestrictedGraph
    ) -> "IntervalCalculation":
        """
        Create an interval given the from/to stops.
        """
        fastest_path = shortest_path = None
        if not should_ignore_interval(interval):
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


IGNORE_RE = re.compile(r"\d|Inbound|Outbound")
IGNORED_PAIRS = {
    ("4191", "4277"),  # N Main St opp Short St to N Main St opp Memorial Pkwy
    (
        "73619",
        "89617",
    ),  # 205 Washington St @ East Walpole Loop to 238 Washington St opp May St
    (
        "109898",
        "109821",
    ),  # Shirley St @ Washington Ave to Veterans Rd @ Washington Ave
    ("censq", "16653"),  # Lynn New Busway to Market St @ Commuter Rail
    ("14748", "censq"),  # Lynn Commuter Rail Busway to Lynn New Busway
    ("fell", "5333"),  # Fellsway Garage to Salem St @ Fellsway Garage
    ("ncamb", "12295"),  # North Cambridge trackless to North Cambridge Carhouse
    ("12295", "ncamb"),  # North Cambridge Carhouse to North Cambridge trackless
}


def should_ignore_interval(interval: Interval) -> bool:
    """
    Return True if we should ignore the given interval.

    - If the descriptions are the same, except for digits (Busway Berth 1 to Busway Berth 2)
    - If the descriptions are the same, except for Inbound/Outbound
    - If the stops are in one of a few specifically ignored pairs of stops
    """
    from_stop = interval.from_stop
    to_stop = interval.to_stop
    return (from_stop.id, to_stop.id) in IGNORED_PAIRS or IGNORE_RE.sub(
        "", from_stop.description
    ) == IGNORE_RE.sub("", to_stop.description)
