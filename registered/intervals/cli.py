"""
Shared code for the `missing_intervals` and `stop_intervals` scripts.
"""

from typing import Callable, Optional
import osmnx as ox
from .page import Page
from .routing import RestrictedGraph, configure_osmnx
from .interval import Interval
from .calculation import IntervalCalculation


def enable_logging() -> None:
    """
    Configure OSMnx to log to stdout.
    """
    configure_osmnx(log_console=True)


def log(line: str) -> None:
    """
    Log a message.

    Uses the OSMnx logger.
    """
    ox.utils.log(line)


def page_from_rows(
    rows: list[str], interval_filter: Optional[Callable[[Interval], bool]] = None
) -> Optional[Page]:
    """
    Process the given list of rows into a Page.
    """
    intervals = sorted(Interval.from_row(row) for row in rows)

    if interval_filter:
        intervals = [interval for interval in intervals if interval_filter(interval)]

    return page_from_intervals(intervals)


def page_from_intervals(intervals: list[Interval]) -> Optional[Page]:
    """
    Process the given list of Intervals into a Page.

    If there are no intervals, return None.
    """
    if not any(True for interval in intervals if interval.is_located()):
        ox.utils.log("No intervals with locations to process.")
        return None

    row_count = len(intervals)

    (from_stops, to_stops) = zip(
        *(
            (interval.from_stop, interval.to_stop)
            for interval in intervals
            if interval.is_located()
        )
    )
    graph = RestrictedGraph.from_points(from_stops + to_stops)

    page = Page(graph=graph)

    for index, interval in enumerate(intervals, 1):
        ox.utils.log(f"processing row {index} of {row_count}: {interval!r}")
        calc = IntervalCalculation.calculate(interval=interval, graph=graph)
        page.add(calc)

    return page
