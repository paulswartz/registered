"""
Parser(s) for the TransitMaster export files.
"""
from datetime import datetime, date
import attr


def parse_lines(lines):
    """
    Parse an iterator of lines into an iterator of records.
    """
    for line in lines:
        [tag, *parts] = line.split(";")
        klass = TAG_TO_CLASS[tag]
        try:
            yield klass.from_line(parts)
        except ValueError as exc:
            raise ValueError(f"unable to parse line: {line}") from exc


def strip_whitespace(string):
    """
    Converter to strip whitespace from a provided string.
    """
    return string.strip()


def optional_int(string_or_int):
    """
    Converter for integers which can optionally be missing (represented by None).
    """
    if isinstance(string_or_int, int):
        return string_or_int

    if string_or_int.strip() == "":
        return None

    return int(string_or_int)


def boolean_integer(string_or_bool):
    """
    Converter to convert a boolean or "0"/"1" string to a boolean.
    """
    if isinstance(string_or_bool, bool):
        return string_or_bool

    if string_or_bool.strip() == "1":
        return True

    return False


def strip_timepoints(timepoint_list):
    """
    Converter to convert a list of timepoints with whitespace to a regular list.
    """
    return [s.strip() for s in timepoint_list if s.strip() != ""]


def iso_date(string_or_date):
    """
    Converter from ISO dates (DDMMYYYY) to a `datetime.date`.
    """
    if isinstance(string_or_date, date):
        return string_or_date

    return datetime.strptime(string_or_date.strip(), "%d%m%Y").date()


@attr.s
class Pattern:  # pylint: disable=too-few-public-methods
    """
    A unique description for a list of stops.
    """

    route_id = attr.ib(converter=strip_whitespace)
    pattern_id = attr.ib()
    direction_name = attr.ib(converter=strip_whitespace)
    sign_code = attr.ib(converter=optional_int)
    variant = attr.ib(converter=strip_whitespace)
    variant_name = attr.ib()

    @classmethod
    def from_line(cls, parts):
        """
        Convert a list of parts to a Pattern.
        """
        [
            route,
            pattern_id,
            direction_name,
            _a,
            sign_code,
            _b,
            variant,
            variant_name,
            *_c,
        ] = parts
        return cls(route, pattern_id, direction_name, sign_code, variant, variant_name)


@attr.s
class PatternStop:  # pylint: disable=too-few-public-methods
    """
    A stop on a Pattern.
    """

    stop_id = attr.ib(converter=strip_whitespace)
    timepoint_id = attr.ib(converter=strip_whitespace)
    sign_code = attr.ib(converter=optional_int)
    is_timepoint = attr.ib(converter=boolean_integer)

    @classmethod
    def from_line(cls, parts):
        """
        Convert a list of parts to a PatternStop
        """
        [stop_id, timepoint_id, sign_code, is_timepoint, _a] = parts
        return cls(stop_id, timepoint_id, sign_code, is_timepoint)


@attr.s
class TimepointPattern:  # pylint: disable=too-few-public-methods
    """
    A list of timepoints for a given route pattern.
    """

    route_id = attr.ib(converter=strip_whitespace)
    direction_name = attr.ib(converter=strip_whitespace)
    timepoint_pattern_id = attr.ib(converter=strip_whitespace)
    timepoints = attr.ib(converter=strip_timepoints)

    @classmethod
    def from_line(cls, parts):
        """
        Convert a list of parts to a TimepointPattern.
        """
        [route_id, direction_name, _a, timepoint_pattern_id, *timepoints, _b] = parts
        return cls(route_id, direction_name, timepoint_pattern_id, timepoints)


@attr.s
class Calendar:  # pylint: disable=too-few-public-methods
    """
    A start/end date range for a garage.
    """

    start_date = attr.ib(converter=iso_date)
    end_date = attr.ib(converter=iso_date)
    garage = attr.ib(converter=strip_whitespace)

    @classmethod
    def from_line(cls, parts):
        """
        Convert a list of parts to a Calendar.
        """
        [start_date, end_date, garage, _a] = parts
        return cls(start_date, end_date, garage)


@attr.s
class CalendarDate:  # pylint: disable=too-few-public-methods
    """
    A specific date for which a service is active.
    """

    date = attr.ib(converter=iso_date)
    garage = attr.ib(converter=strip_whitespace)
    service_key = attr.ib(converter=lambda x: strip_whitespace(x)[-3:])
    day_type = attr.ib(converter=strip_whitespace)

    @classmethod
    def from_line(cls, parts):
        """
        Convert a list of parts to a CalendarDate.
        """
        [cal_date, garage, extended_service_key, day_type, *_rest] = parts
        return cls(cal_date, garage, extended_service_key, day_type)


@attr.s
class Stop:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """
    A stop.
    """

    stop_id = attr.ib(converter=strip_whitespace)
    name = attr.ib(converter=strip_whitespace)
    timepoint_id = attr.ib(converter=strip_whitespace)
    latitude = attr.ib(converter=float)
    longitude = attr.ib(converter=float)
    on_street = attr.ib(converter=strip_whitespace)
    at_street = attr.ib(converter=strip_whitespace)
    municipality = attr.ib(converter=strip_whitespace)
    in_service = attr.ib(converter=boolean_integer)

    @classmethod
    def from_line(cls, parts):
        """
        Covert a list of parts to a Stop.
        """
        [
            stop_id,
            name,
            timepoint_id,
            latitude,
            longitude,
            on_street,
            at_street,
            _,
            _,
            municipality,
            _,
            in_service,
            *_rest,
        ] = parts
        return cls(
            stop_id,
            name,
            timepoint_id,
            latitude,
            longitude,
            on_street,
            at_street,
            municipality,
            in_service,
        )


TAG_TO_CLASS = {
    "PAT": Pattern,
    "TPS": PatternStop,
    "PPAT": TimepointPattern,
    "CAL": Calendar,
    "DAT": CalendarDate,
    "STP": Stop,
}
