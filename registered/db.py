"""
Functions for accessing data from the TransitMaster database.
"""
import itertools
import os
import pyodbc

CONN = None


def sql_driver():
    """
    Returns the appropriate SQL Server driver for the current OS.
    """
    if os.name == "nt":
        return "{ODBC Driver 17 for SQL Server}"

    if os.name == "posix":
        return "/usr/local/lib/libtdsodbc.so"

    raise RuntimeError("unknown OS: " + os.name)


def conn():
    """
    Returns the global database connection.
    """
    global CONN  # pylint: disable=global-statement
    if CONN is None:
        CONN = pyodbc.connect(
            driver=sql_driver(),
            server=os.environ["TRANSITMASTER_SERVER"],
            database="TMMain",
            user=os.environ["TRANSITMASTER_UID"],
            password=os.environ["TRANSITMASTER_PWD"],
        )
    return CONN


def grouper(iterable, chunk_size):
    """
    Group an iterable into lists of length chunk_size.

    From: https://stackoverflow.com/a/29524877
    """
    iterable = iter(iterable)
    while True:
        chunk = list(itertools.islice(iterable, chunk_size))
        if chunk == []:
            break
        yield chunk


def maybe_float(string_or_none):
    """
    Parse a string into a float, or None.
    """
    if string_or_none in {None, ""}:
        return None

    return float(string_or_none)


def geo_node(abbrs):  # pylint: disable=inconsistent-return-statements
    """
    Given a list of stop IDs, returns an iterator of tuples: (id, name, lat, lon).
    """
    try:
        cursor = conn().cursor()
    except pyodbc.OperationalError:
        return []

    for chunk in grouper(abbrs, 50):
        question_marks = ", ".join("?" for _ in chunk)
        result = cursor.execute(
            "SELECT GEO_NODE_ABBR,GEO_NODE_NAME,"
            "MDT_LATITUDE/10000000,"
            "MDT_LONGITUDE/10000000 "
            "FROM GEO_NODE "
            f"WHERE GEO_NODE_ABBR IN ({question_marks});",
            chunk,
        )
        for (stop_id, stop_name, lat, lon) in result:
            yield (stop_id, stop_name, maybe_float(lat), maybe_float(lon))
