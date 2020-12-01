"""
Functions for accessing data from the TransitMaster database.
"""
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


def geo_node(abbrs):  # pylint: disable=inconsistent-return-statements
    """
    Given a list of stop IDs, returns an iterator of tuples: (id, name, lat, lon).
    """
    try:
        cursor = conn().cursor()
    except pyodbc.OperationalError:
        return []

    question_marks = ", ".join("?" for _ in abbrs)
    result = cursor.execute(
        "SELECT GEO_NODE_ABBR,GEO_NODE_NAME,"
        "MDT_LATITUDE/10000000,"
        "MDT_LONGITUDE/10000000 "
        "FROM GEO_NODE "
        f"WHERE GEO_NODE_ABBR IN ({question_marks});",
        list(abbrs),
    )
    for (stop_id, stop_name, lat, lon) in result:
        yield (stop_id, stop_name, float(lat), float(lon))
