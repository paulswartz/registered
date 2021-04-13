from registered.intervals.stop import Stop
from shapely.geometry import Point


class TestStop:
    def test_from_tuple(self):
        actual = Stop(("-1", "-2"), id="123", description="hi")
        assert actual.id == "123"
        assert actual.description == "hi"
        assert actual.wkt == "POINT (-1 -2)"
        assert actual.x == -1
        assert actual.y == -2
        assert repr(actual) == "Stop(POINT (-1 -2), id='123', description='hi')"

    def test_from_point(self):
        actual = Stop(Point((2, 3)), id="456")
        assert actual.id == "456"
        assert actual.description is None
        assert actual.wkt == "POINT (2 3)"
        assert actual.x == 2
        assert actual.y == 3
