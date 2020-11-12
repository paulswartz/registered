from datetime import date
from registered import parser


def test_parser_PAT_TPS():
    lines = [
        "PAT;   90;0090_0047;Inbound   ; 4;907     ;1;_       ;Davis Station - Assembly Row",
        "TPS;5104    ;davis ;907     ;1; ",
    ]
    expected = [
        parser.Pattern(
            route="90",
            pattern_id="0090_0047",
            direction_name="Inbound",
            sign_code=907,
            variant="_",
            variant_name="Davis Station - Assembly Row",
        ),
        parser.PatternStop(
            stop_id="5104",
            timepoint_id="davis",
            sign_code=907,
            is_timepoint=True,
        ),
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected


def test_parser_missing_sign_code():
    lines = [
        "PAT;9903 ;099030001;Inbound   ; 4;        ;X;  ;                                        ;9903",
        "TPS;5104    ;davis ;        ;1;",
    ]
    [pattern, pattern_stop] = list(parser.parse_lines(lines))
    assert pattern.sign_code is None
    assert pattern_stop.sign_code is None


def test_parser_PPAT():
    lines = [
        "PPAT;   90;Inbound   ; 4;90_iv_2   ;davis ;hlscl ;sull  ;amall ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;90"
    ]
    expected = [
        parser.TimepointPattern(
            route_id="90",
            direction_name="Inbound",
            timepoint_pattern_id="90_iv_2",
            timepoints=["davis", "hlscl", "sull", "amall"],
        )
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected


def test_parser_CAL_DAT():
    lines = [
        "CAL;15032020;20062020;Cabot   ;        ",
        "DAT;15032020;Cabot   ;abc20017;Sunday    ; 6;02;BUS22020  ;Cabot   ;hbc20017;Sunday    ; 6;02;BUS22020  ",
    ]
    expected = [
        parser.Calendar(
            start_date=date(2020, 3, 15), end_date=date(2020, 6, 20), garage="Cabot"
        ),
        parser.CalendarDate(
            date=date(2020, 3, 15), garage="Cabot", service_key="017", day_type="Sunday"
        ),
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected
