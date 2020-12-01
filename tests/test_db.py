from registered import db


def test_grouper_list():
    original = [1, 2, 3, 4, 5, 6, 7]
    expected = [[1, 2], [3, 4], [5, 6], [7]]
    actual = list(db.grouper(original, 2))

    assert actual == expected


def test_grouper_list_exact_size():
    original = [1, 2, 3, 4, 5, 6]
    expected = [[1, 2], [3, 4], [5, 6]]
    actual = list(db.grouper(original, 2))

    assert actual == expected


def test_grouper_iterable():
    original = range(7)
    expected = [[0, 1, 2], [3, 4, 5], [6]]
    actual = list(db.grouper(original, 3))

    assert actual == expected
