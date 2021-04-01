from shapely.geometry import Point
from registered.missing_intervals import parse_rows, Interval, Stop


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


def test_basic_workflow():
    rows = [
        {
            "issueid": "1",
            "routeversionid": "138.2",
            "IntervalType": "--",
            "FromStopNumber": "5774",
            "FromStopDescription": "Revere St @ Sagamore St",
            "ToStopNumber": "15795",
            "ToStopDescription": "Wonderland Busway",
            "IntervalDescription": "116-Outbound-116-4",
        }
    ]
    page = parse_rows(rows)
    page.render()
