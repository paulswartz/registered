from registered.intervals.stop import Stop
from registered.intervals.interval import Interval, IntervalType


class TestInterval:
    def test_from_row(self):
        row = {
            "issueid": "1",
            "routeversionid": "138.2",
            "IntervalId": "1234",
            "IntervalType": "0",
            "FromStopNumber": "5774",
            "FromStopDescription": "Revere St @ Sagamore St",
            "FromStopLatitude": "42.418574",
            "FromStopLongitude": "-70.99272",
            "ToStopNumber": "15795",
            "ToStopDescription": "Wonderland Busway",
            "ToStopLatitude": "42.413385",
            "ToStopLongitude": "-70.99205",
            "IntervalDescription": "116-Outbound-116-4",
        }
        expected = Interval(
            id=1234,
            type=IntervalType.REVENUE,
            from_stop=Stop(
                (-70.992792, 42.418574),
                id="5774",
                description="Revere St @ Sagamore St",
            ),
            to_stop=Stop(
                (-70.99205, 42.413385), id="15795", description="Wonderland Busway"
            ),
            description="116-Outbound-116-4",
        )
        actual = Interval.from_row(row)
        assert expected == actual
