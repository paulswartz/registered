from datetime import date
from registered.cheat_sheet import *
from registered.parser import CalendarDate


class TestExceptionCombination:
    def test_str_simple(self):
        combo = ExceptionCombination("011")
        assert str(combo) == "011"

    def test_str_with_exceptions(self):
        combo = ExceptionCombination(
            "016",
            garage_exceptions={"sa6": {"BennTT", "Somvl"}, "os6": {"Albny"}},
        )
        assert str(combo) == "016, os6 (Albny), sa6 (BennTT, Somvl)"

    def test_str_take_out(self):
        combo = ExceptionCombination(
            "016",
            garage_exceptions={"l36": {"Somvl"}},
        )
        assert str(combo) == "016, l36 (Somvl) *** TAKE THIS OUT"

    def test_from_garages_simple(self):
        garages = {"Albny": "011", "Arbor": "011"}
        expected = ExceptionCombination("011")
        actual = ExceptionCombination.from_garages(garages)

        assert expected == actual

    def test_from_garages_with_exceptions(self):
        garages = {
            "BenTT": "016",
            "Cabot": "sa6",
            "Charl": "016",
            "Fells": "016",
            "Somvl": "sa6",
        }
        expected = ExceptionCombination("016", {"sa6": {"Cabot", "Somvl"}})
        actual = ExceptionCombination.from_garages(garages)

        assert expected == actual

    def test_from_garages_without_service(self):
        garages = {
            "BenTT": "016",
            "Fells": "016",
            "Somvl": "",
        }
        expected = ExceptionCombination("016")
        actual = ExceptionCombination.from_garages(garages)

        assert expected == actual

    def test_should_take_out(self):
        assert ExceptionCombination("011").should_take_out() == False
        assert ExceptionCombination("l31").should_take_out()
        assert ExceptionCombination("a31").should_take_out()
        assert ExceptionCombination("b41").should_take_out()
        assert ExceptionCombination("we1").should_take_out()
        assert ExceptionCombination("016", garage_exceptions={"l36": {"Somvl"}}).should_take_out()


class TestCheatSheet:
    def test_from_records_simple(self):
        records = [
            CalendarDate(
                date=date(2020, 12, 20),
                garage="Albny",
                service_key="017",
                day_type="Sunday",
            ),
            CalendarDate(
                date=date(2020, 12, 21),
                garage="Albny",
                service_key="011",
                day_type="Weekday",
            ),
            CalendarDate(
                date=date(2020, 12, 22),
                garage="Albny",
                service_key="011",
                day_type="Weekday",
            ),
            CalendarDate(
                date=date(2020, 12, 23),
                garage="Albny",
                service_key="l31",
                day_type="Weekday",
            ),
            CalendarDate(
                date=date(2020, 12, 26),
                service_key="016",
                garage="Albny",
                day_type="Saturday",
            ),
        ]
        actual = CheatSheet.from_records(records)
        assert actual.season_name == "Winter"
        assert actual.start_date == date(2020, 12, 20)
        assert actual.end_date == date(2020, 12, 26)
        assert actual.weekday_base == ExceptionCombination("011")
        assert actual.saturday_base == ExceptionCombination("016")
        assert actual.sunday_base == ExceptionCombination("017")
        assert actual.date_combos == {date(2020, 12, 23): ExceptionCombination("l31")}
