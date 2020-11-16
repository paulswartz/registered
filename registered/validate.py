"""
CLI tool to validate a given HASTUS export for import to TransitMaster.
"""
import argparse
from registered.rating import Rating
from registered import validators


def validate_rating(rating):
    """
    Validate a given Rating, printing errors and returning True if there were errors.
    """
    seen_errors = set()
    for validator in validators.ALL_VALIDATORS:
        for error in validator(rating):
            if error not in seen_errors:
                print(error)
                seen_errors.add(error)
    return seen_errors != set()


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    path = args.DIR
    if validate_rating(Rating(path)):
        return 1

    return 0


parser = argparse.ArgumentParser(
    description="Validate the HASTUS export files (post-merge)"
)
parser.add_argument("DIR", help="The Combine directory where all the files live")

if __name__ == "__main__":
    import sys

    sys.exit(main(parser.parse_args()))
