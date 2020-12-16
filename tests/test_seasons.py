from datetime import date
import random
import pytest
from registered import seasons


def test_sort_key_hastus_export():
    expected = ["Summer 2020", "Fall 2020", "Winter 2021", "Spring 2021"]
    shuffled = random.sample(expected, len(expected))
    assert sorted(shuffled, key=seasons.sort_key_hastus_export) == expected


@pytest.mark.parametrize(
    "date,season",
    [
        (date(2020, 8, 30), "Fall"),
        (date(2019, 9, 1), "Fall"),
        (date(2020, 3, 15), "Spring"),
        (date(2020, 4, 6), "Spring"),
        (date(2020, 6, 21), "Summer"),
        (date(2020, 12, 20), "Winter"),
    ],
)
def test_season_for_date(date, season):
    assert seasons.season_for_date(date) == season
