"""
CLI tool to output the calendar for each garage
"""
import argparse
from registered.rating import Rating
from registered.parser import CalendarDate


def calendar(rating):
    """
    Generate the calendar for a given rating.
    """
    cal = rating["cal"]
    garages = set()
    dates = set()
    services = {}
    for record in cal:
        if not isinstance(record, CalendarDate):
            continue
        garages.add(record.garage)
        dates.add(record.date)
        key = (record.date, record.garage)
        services[key] = record.service_key

    garages = sorted(garages)

    yield ["date", *garages]

    for date in sorted(dates):
        date_str = date.strftime("%Y-%m-%d")
        garage_values = (services.get((date, garage), "") for garage in garages)
        yield [date_str, *garage_values]


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    path = args.DIR
    for row in calendar(Rating(path)):
        print(",".join(row))


parser = argparse.ArgumentParser(
    description="Print the calendar from the HASTUS export files (post-merge)"
)
parser.add_argument("DIR", help="The Combine directory where all the files live")

if __name__ == "__main__":
    main(parser.parse_args())
