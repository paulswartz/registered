"""
Parser(s) for the TransitMaster export files.
"""
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


@attr.s
class Pattern:  # pylint: disable=too-few-public-methods
    """
    A unique description for a list of stops.
    """

    route = attr.ib(converter=strip_whitespace)
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
        [route_id, direction_name, _a, timepoint_pattern_id, *timepoints] = parts
        return cls(route_id, direction_name, timepoint_pattern_id, timepoints)


TAG_TO_CLASS = {"PAT": Pattern, "TPS": PatternStop, "PPAT": TimepointPattern}
