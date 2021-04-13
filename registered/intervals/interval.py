"""
Generic representation of an interval in TransitMaster.
"""
from enum import IntEnum
from typing import Any, Optional, Tuple, Union
import attr
from shapely.geometry import Point
from .stop import Stop


class IntervalType(IntEnum):
    """
    Type of interval.
    """

    REVENUE = 0
    DEADHEAD = 1
    PULLOUT = 2
    PULLIN = 3

    @classmethod
    def optional(
        cls, value: Optional[Union[int, str, "IntervalType"]]
    ) -> Optional["IntervalType"]:
        """
        Convert an Optional int/str/IntervalType into an Optional[IntervalType].
        """
        if value is None:
            return value

        return cls(int(value))


def optional_int(value: Optional[Union[int, str]]) -> Optional[int]:
    """
    Convert an Optional string/int into an Optional[int].
    """
    if value is None:
        return value

    return int(value)


@attr.define(kw_only=True)
class Interval:
    """
    A link between two points.
    """

    id: Optional[int] = attr.ib(default=None, converter=optional_int)
    type: Optional[IntervalType] = attr.ib(
        default=None, converter=IntervalType.optional
    )
    from_stop: Stop
    to_stop: Stop
    description: Optional[str] = attr.ib(default=None)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Interval":
        """
        Convert a CSV or database row to an Interval.
        """
        from_stop = Stop(
            (row["FromStopLongitude"], row["FromStopLatitude"]),
            id=row["FromStopNumber"],
            description=row["FromStopDescription"],
        )
        to_stop = Stop(
            (row["ToStopLongitude"], row["ToStopLatitude"]),
            id=row["ToStopNumber"],
            description=row["ToStopDescription"],
        )

        return cls(
            id=optional_int(row.get("IntervalId")),
            description=row.get("IntervalDescription"),
            from_stop=from_stop,
            to_stop=to_stop,
            type=IntervalType.optional(row.get("IntervalType")),
        )
