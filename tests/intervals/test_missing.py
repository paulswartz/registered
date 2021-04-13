from shapely.geometry import Point
from registered.intervals.stop import Stop
from registered.intervals.missing import parse_rows, Interval


class TestInterval:
    def test_should_ignore(self):
        point = Point(0, 0)
        sullivan_1 = Stop(
            point, id="29001", description="Sullivan Station Busway - Berth 1"
        )
        sullivan_2 = Stop(
            point, id="20002", description="Sullivan Station Busway - Berth 2"
        )
        fields_corner = Stop(point, id="323", description="Fields Corner Busway")
        chelsea_inbound = Stop(point, id="74630", description="Chelsea - Inbound")
        chelsea_outbound = Stop(point, id="74631", description="Chelsea - Outbound")

        assert Interval.should_ignore(sullivan_1, sullivan_1)
        assert Interval.should_ignore(sullivan_1, sullivan_2)
        assert Interval.should_ignore(sullivan_1, fields_corner) == False
        assert Interval.should_ignore(chelsea_inbound, chelsea_outbound)


def test_empty():
    rows = []
    assert parse_rows(rows) is None


def test_basic_workflow():
    rows = [
        {
            "issueid": "1",
            "routeversionid": "138.2",
            "IntervalType": "--",
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
    ]
    page = parse_rows(rows)
    page.render()


def test_ignored_row():
    rows = [
        {
            "issueid": "1",
            "routeversionid": "138.2",
            "IntervalType": "DH",
            "FromStopNumber": "32001",
            "FromStopDescription": "Quincy Center Busway",
            "FromStopLatitude": "42.251696",
            "FromStopLongitude": "-71.004973",
            "ToStopNumber": "32004",
            "ToStopDescription": "Quincy Center Busway",
            "ToStopLatitude": "42.251772",
            "ToStopLongitude": "-71.005099",
            "IntervalDescription": "220-Outbound-220-3",
        }
    ]
    page = parse_rows(rows, include_ignored=True)
    page.render()
