"""
Generic representation of an interval in TransitMaster.
"""
from enum import IntEnum
from typing import Any, Optional, Tuple, Union
import attr
from shapely.geometry import Point


@attr.define(repr=False)
class Stop(Point):
    """
    A location at one end of an interval (either start or end).
    """

    # pylint: disable=too-few-public-methods
    _point: Union[Point, Tuple[Union[float, str]]]
    id: str = attr.ib(kw_only=True)
    description: Optional[str] = attr.ib(default=None, kw_only=True)

    def __attrs_post_init__(self):
        if not isinstance(self._point, Point):
            self._point = Point([float(val) for val in self._point])
        Point.__init__(self, self._point)
        self._point = None

    def __repr__(self):
        return f"Stop(Point({self.x!r}, {self.y!r}), id={self.id!r}, description={self.description!r})"


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
    distance_between_map: Optional[int] = attr.ib(default=None)
    distance_between_measured: Optional[int] = attr.ib(default=None)
    compass_direction: Optional[int] = attr.ib(default=None)

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
            distance_between_map=optional_int(row.get("DistanceBetweenMap")),
            distance_between_measured=optional_int(row.get("DistanceBetweenMeasured")),
            compass_direction=optional_int(row.get("CompassDirection")),
        )
