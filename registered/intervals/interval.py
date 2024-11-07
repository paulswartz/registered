"""
Generic representation of an interval in TransitMaster.
"""

from enum import IntEnum
from functools import total_ordering
from typing import Any, Optional, Union
import attr
from shapely.geometry import Point


@attr.define
class Stop:
    """
    A location at one end of an interval (either start or end).
    """

    # pylint: disable=invalid-name,missing-function-docstring
    point: Point = attr.ib(converter=Point)
    id: str
    description: Optional[str] = attr.ib(default=None)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return (
            f"Stop(Point({self.point.x!r}, {self.point.y!r}), "
            f"id={self.id!r}, description={self.description!r})"
        )

    @property
    def wkt(self):
        return self.point.wkt

    @property
    def x(self):
        return self.point.x

    @property
    def y(self):
        return self.point.y

    @staticmethod
    def from_row(
        lat_str: str, lon_str: str, id_: str, description: str
    ) -> Union["Stop", "StopWithoutLocation"]:
        """
        Try to parse a Stop, and return either a Stop or a StopWithoutLocation.
        """
        try:
            return Stop((lat_str, lon_str), id=id_, description=description)
        except ValueError:
            return StopWithoutLocation(id=id, description=description)


@attr.define
class StopWithoutLocation:
    """
    Represents a stop for which we don't have a location.
    """

    # pylint: disable=too-few-public-methods

    id: str
    description: Optional[str] = attr.ib(default=None)


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
    if value is None or value == "":
        return None

    return int(value)


@total_ordering
@attr.define(kw_only=True)
class Interval:
    """
    A link between two points.
    """

    # pylint: disable=invalid-name
    id: Optional[int] = attr.ib(default=None, converter=optional_int)
    type: Optional[IntervalType] = attr.ib(
        default=None, converter=IntervalType.optional
    )
    from_stop: Union[Stop, StopWithoutLocation]
    to_stop: Union[Stop, StopWithoutLocation]
    route: Optional[str] = attr.ib(default=None)
    direction: Optional[str] = attr.ib(default=None)
    pattern: Optional[str] = attr.ib(default=None)
    distance_between_map: Optional[int] = attr.ib(default=None)
    distance_between_measured: Optional[int] = attr.ib(default=None)

    def is_located(self):
        """
        True if both from_stop and to_stop have a location.
        """
        return isinstance(self.from_stop, Stop) and isinstance(self.to_stop, Stop)

    def __lt__(self, other):
        """
        Returns True if this interval has a lower pattern/direction compared to `other`.
        """
        if isinstance(other, Interval):
            return (self.pattern, self.direction, self.id) < (
                other.pattern,
                other.direction,
                other.id,
            )

        return NotImplemented

    @property
    def description(self) -> Optional[str]:
        """
        Backwards-compatibility to generate a description from the route/direction/pattern.
        """
        if self.route is None and self.direction is None and self.pattern is None:
            return None
        return f"{self.route}-{self.direction}-{self.pattern}"

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Interval":
        """
        Convert a CSV or database row to an Interval.
        """
        from_stop = Stop.from_row(
            row["FromStopLongitude"],
            row["FromStopLatitude"],
            row["FromStopNumber"],
            row["FromStopDescription"],
        )
        to_stop = Stop.from_row(
            row["ToStopLongitude"],
            row["ToStopLatitude"],
            row["ToStopNumber"],
            row["ToStopDescription"],
        )

        description = row.get("IntervalDescription")
        if description is not None:
            (route, direction, pattern) = description.split("-", 2)
        else:
            route = row.get("Route")
            direction = row.get("Direction")
            pattern = row.get("Pattern")

        return cls(
            id=optional_int(row.get("IntervalId")),
            from_stop=from_stop,
            to_stop=to_stop,
            route=route,
            direction=direction,
            pattern=pattern,
            type=IntervalType.optional(row.get("IntervalType")),
            distance_between_map=optional_int(row.get("DistanceBetweenMap")),
            distance_between_measured=optional_int(row.get("DistanceBetweenMeasured")),
        )
