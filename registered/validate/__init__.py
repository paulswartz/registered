"""
CLI tool to validate a given HASTUS export for import to TransitMaster.
"""

import argparse
from registered.rating import Rating
from registered.validate.validators import ALL_VALIDATORS


def validate_rating(rating):
    """
    Validate a given Rating, yielding errors.
    """
    seen_errors = set()
    for validator in ALL_VALIDATORS:
        for error in validator(rating):
            if error not in seen_errors:
                yield error
                seen_errors.add(error)


def validate_path(path):
    """
    Validate a gvien path.

    Returns 0 if the path is valid, 1 (and prints the errors) otherwise.
    """
    exit_code = 0
    for error in validate_rating(Rating(path)):
        print(error)
        exit_code = 1

    return exit_code


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    path = args.DIR
    return validate_path(path)


PARSER = argparse.ArgumentParser(
    description="Validate the HASTUS export files (post-merge)"
)
PARSER.add_argument("DIR", help="The Combine directory where all the files live")
