from shapely.geometry import Point
from registered.intervals.missing import parse_rows, Interval, Stop


class TestInterval:
    def test_should_ignore(self):
        point = Point(0, 0)
        sullivan_1 = Stop("29001", "Sullivan Station Busway - Berth 1", point)
        sullivan_2 = Stop("20002", "Sullivan Station Busway - Berth 2", point)
        fields_corner = Stop("323", "Fields Corner Busway", point)
        chelsea_inbound = Stop("74630", "Chelsea - Inbound", point)
        chelsea_outbound = Stop("74631", "Chelsea - Outbound", point)

        assert Interval.should_ignore(sullivan_1, sullivan_1)
        assert Interval.should_ignore(sullivan_1, sullivan_2)
        assert Interval.should_ignore(sullivan_1, fields_corner) == False
        assert Interval.should_ignore(chelsea_inbound, chelsea_outbound)


class TestStop:
    def test_repr(self):
        stop = Stop("123", "Description", Point(-71, 40))
        assert (
            repr(stop)
            == "Stop(id='123', description='Description', point=POINT (-71 40))"
        )


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
