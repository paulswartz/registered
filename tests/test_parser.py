from datetime import date, time
import pytest
from registered import parser


def test_transitmaster_time():
    assert parser.transitmaster_time("0123a") == time(1, 23)
    assert parser.transitmaster_time("1055p") == time(22, 55)
    assert parser.transitmaster_time("1200a") == time(0, 0)
    assert parser.transitmaster_time("1200p") == time(12, 0)
    assert parser.transitmaster_time("1200x") == time(0, 0)


def test_TripRevenueType_for_trip():
    assert parser.TripRevenueType.for_trip("0") == parser.TripRevenueType.NON_REVENUE
    assert parser.TripRevenueType.for_trip(" ") == parser.TripRevenueType.NON_REVENUE
    assert parser.TripRevenueType.for_trip("1") == parser.TripRevenueType.REVENUE
    assert parser.TripRevenueType.for_trip("X") == parser.TripRevenueType.OPPORTUNITY


def test_Stop_latitude_longitude():
    stop = parser.Stop(
        stop_id="",
        name="",
        timepoint_id="",
        on_street="",
        at_street="",
        municipality="",
        in_service=False,
        easting_ft=768989.0,
        northing_ft=2945910.0,
    )
    assert stop.latlon() == pytest.approx((42.330957, -71.082754))


def test_parser_PAT_TPS():
    lines = [
        "PAT;   90;0090_0047;Inbound   ; 4;907     ;1;_       ;Davis Station - Assembly Row",
        "TPS;5104    ;davis ;907     ;1; ",
        "TPS;00009   ;arbor ;        ;X; ",
    ]
    expected = [
        parser.Pattern(
            route_id="90",
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
            revenue_type=parser.TripRevenueType.REVENUE,
        ),
        parser.PatternStop(
            stop_id="00009",
            timepoint_id="arbor",
            sign_code=None,
            revenue_type=parser.TripRevenueType.OPPORTUNITY,
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


def test_parser_STP():
    lines = [
        "STP;10000   ;Tremont St opp Temple Pl                          ;pktrm ;  774308.2; 2954951.1;WINTER STREET                                     ;TEMPLE PLACE                                      ;     ;    ;boston;        ;1;     ; 19.9"
    ]
    expected = [
        parser.Stop(
            stop_id="10000",
            name="Tremont St opp Temple Pl",
            timepoint_id="pktrm",
            easting_ft=774308.2,
            northing_ft=2954951.1,
            on_street="WINTER STREET",
            at_street="TEMPLE PLACE",
            municipality="boston",
            in_service=True,
        )
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected


def test_parser_VSC_BLK_TIN():
    lines = [
        "VSC;hba20021;Weekday   ; 0;02;BUS22020  ;Albny   ;Albany Weekday",
        "BLK;   A57-11;   4245117;12345  ;albny ;0415a;wtryd ;0430a;kenbs ;0908a;albny ;0929a;    ;    ;        ;021;;",
        "TIN;  43858890",
    ]
    expected = [
        parser.Version(
            service_key="021",
            day_type="Weekday",
            garage="Albny",
            description="Albany Weekday",
        ),
        parser.Block(
            block_id="A57-11",
            piece_id="4245117",
            service_key="021",
            times=[
                ("albny", time(4, 15)),
                ("wtryd", time(4, 30)),
                ("kenbs", time(9, 8)),
                ("albny", time(9, 29)),
            ],
        ),
        parser.TripIdentifier(trip_id="43858890"),
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected


def test_parser_BLK_unusual():
    lines = [
        "BLK;    P-P13;   4202004;12345  ;prwb  ;0750p;orhgt ;0810p;orhgt ;1235x;prwb  ;1245x;    ;    ;        ;011;;",
        "BLK;   T70-40;   4214397;12345  ;somvl ;0410a;unvpk ;0428a;kndl  ;1031p;somvl ;1046p;4YE_;    ;        ;021;;",
        "BLK;  S743-72;   4240570;12345  ;soham ;0358a;conrd ;0413a;conrd ;0614p;soham ;0629p;6SD_;6SD_;        ;011;;",
    ]
    actual = list(parser.parse_lines(lines))

    assert actual != []


def test_parser_TRP():
    lines = [
        "TRP;  43857823;        ;12345  ;  193;0193_0029;Regular        ; 0;0;1",
        "PTS; 1045a",
        "TRP;   6417265;4    ;12345  ;9903 ;099030001;Regular        ; 0; ;X;9903",
    ]
    expected = [
        parser.Trip(
            trip_id="43857823",
            route_id="193",
            pattern_id="0193_0029",
            description="Regular",
            sequence=0,
            revenue_type=parser.TripRevenueType.REVENUE,
        ),
        parser.TripTime(time=time(10, 45)),
        parser.Trip(
            trip_id="6417265",
            route_id="9903",
            pattern_id="099030001",
            description="Regular",
            sequence=0,
            revenue_type=parser.TripRevenueType.OPPORTUNITY,
        ),
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected


def test_parser_RTE():
    lines = [
        "RTE;   04;   04;Regular   ; 0;Bus       ; 0",
        "RTE;9903 ;9903 ;Regular   ; 0;Bus       ; 0;9903",
    ]
    expected = [
        parser.Route(route_id="04", route_type="Regular", vehicle_type="Bus"),
        parser.Route(route_id="9903", route_type="Regular", vehicle_type="Bus"),
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected


def test_parser_CSC_PCE():
    lines = [
        "CSC;aba11011;Weekday   ; 0;02;BUS12021  ;Albny   ;Albany Weekday REMAKE                                                           ",
        "PCE;123-1501 ;   9911631;12345  ;   4484646;    1;albny ;0405a;albny ;0415a;albny ;0919a;albny ;0919a;011;;",
    ]
    expected = [
        parser.CrewSchedule(
            service_key="011",
            day_type="Weekday",
            garage_name="Albny",
            description="Albany Weekday REMAKE",
        ),
        parser.Piece(
            service_key="011",
            run_id="123-1501",
            piece_id="4484646",
            times=[
                ("albny", time(4, 5)),
                ("albny", time(4, 15)),
                ("albny", time(9, 19)),
                ("albny", time(9, 19)),
            ],
        ),
    ]
    actual = list(parser.parse_lines(lines))

    assert actual == expected
