import pytest
from registered.validate import helpers


@pytest.mark.parametrize(
    "first,second,should_be_equal",
    [
        ([1, 2, 3], [1, 2, 3], True),
        ([1, 2, 3], [1, 2], True),
        ([1, 2, 3], [1, 3], True),
        ([1, 2, 3], [1, 3, 2], False),
        ([1, 2, 1, 3], [1, 2, 3], True),
        ([1, 2], [1, 4], False),
    ],
)
def test_same_list_order(first, second, should_be_equal):
    assert helpers.same_list_order(first, second) == should_be_equal
