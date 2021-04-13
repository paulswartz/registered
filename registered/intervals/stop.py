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
        return f"Stop({self.wkt}, id={self.id!r}, description={self.description!r})"
