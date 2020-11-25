from pathlib import Path
import pytest
from registered import rating, validate

VALID_TESTS_DIR = Path(__file__).parent / "support" / "validation" / "valid"
INVALID_TESTS_DIR = Path(__file__).parent / "support" / "validation" / "invalid"
GLOB = "[!.]*"


def basename(path):
    return path.name


@pytest.mark.parametrize("path", VALID_TESTS_DIR.glob(GLOB), ids=basename)
def test_valid_ratings(path):
    """
    Tests that the given ratings are treated as valid.
    """
    errors = list(validate.validate_rating(rating.Rating(path, expect_all_files=False)))
    assert errors == [], f"expected to see no validation errors in {path}"


@pytest.mark.parametrize("path", INVALID_TESTS_DIR.glob(GLOB), ids=basename)
def test_invalid_ratings(path):
    """
    Tests that the given ratings are treated as invalid.

    Each one has an EXPECTED_ERRORS.txt file in the directory. This is a list
    of lines that are expected to match at least one error.
    """
    errors = list(validate.validate_rating(rating.Rating(path, expect_all_files=False)))
    assert errors != [], f"expected to see validation errors in {path}"
    error_text = "\n".join(repr(e) for e in errors)
    # ensure that we see the expected errors
    with open(path / "EXPECTED_ERRORS.txt") as expected:
        for line in expected:
            line = line.strip()
            if not any(True for error in errors if line in repr(error)):
                raise AssertionError(
                    f"expected to see an error matching {repr(line)}, actual errors:\n{error_text}"
                )
