from registered.intervals.missing import parse_rows


def test_empty():
    rows = []
    assert parse_rows(rows) is None


def test_basic_workflow():
    rows = [
        {
            "issueid": "1",
            "routeversionid": "138.2",
            "IntervalId": 1234,
            "IntervalType": 0,
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
    rendered = page.render()
    assert "5774" in rendered
    assert "Revere St @ Sagamore St" in rendered
    assert "15795" in rendered
    assert "Wonderland Busway" in rendered
    assert "Fastest (red)" in rendered
    assert "Revenue" in rendered, rendered
    assert "116-Outbound-116-4" in rendered, rendered


def test_ignored_row():
    rows = [
        {
            "issueid": "1",
            "routeversionid": "138.2",
            "IntervalId": "1234",
            "IntervalType": "1",
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
