"""
Helper functions for working with the 4 HASTUS seasons.
"""

SEASONS = ["Winter", "Spring", "Summer", "Fall"]


def sort_key_hastus_export(rating_folder):
    """
    Sort the HASTUS exports (which look like "Winter 2021 AVL Data").

    It does this by breaking the name into a tuple (2021, 0, "AVL Data").
    """
    for index, season in enumerate(SEASONS):
        if not rating_folder.startswith(season):
            continue

        year = int(rating_folder[len(season) + 1 : len(season) + 5])
        rest = rating_folder[len(season) + 6 :]
        return (year, index, rest)

    return (0, 0, rating_folder)


def season_for_date(date):
    """
    Returns the season, given the start date of the rating.
    """
    month = date.month
    if month < 3 or month == 12:
        return "Winter"
    if month < 6:
        return "Spring"
    if month < 8:
        return "Summer"

    return "Fall"
