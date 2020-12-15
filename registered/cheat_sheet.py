"""
CLI tool to output the rating cheat sheet.

The cheat sheet has the following info:

- name of the rating (Winter 2021)
- start date (first date the rating is active)
- end date (last date the rating is active)
- base schedules (Weekday, Saturday, Sunday, and any garage-level exceptions)
- dates with exception combinations (incl. garage if needed)
- weekday + test/dead reckoning (ST1 DR1) on the first weekday labeled TAKE THIS OUT
- any `l3*` tags labeled TAKE THIS OUT

## Example

Winter 2021

Sun 12/20/2020 - Sat 3/13/2021

Weekday 011
Saturday 016, sa6 (BennTT, Somvl)
Sunday 017

12/21 011 DR1 ST1 *** TAKE THIS OUT

12/24 ns1
12/25 hl7
12/28 - 12/31 ns1
1/1 hl7

Fri 1/15 l31 *** TAKE THIS OUT
Sat 1/16 016, l36 (Somvl) *** TAKE THIS OUT
Mon 1/18 hl6
Mon 2/15 hl6
2/16 - 2/19 ns1
"""
import sys
import argparse
from collections import defaultdict
import attr
from registered.rating import Rating
from registered.parser import CalendarDate
from registered import seasons


@attr.s
class CheatSheet:
    """
    CheatSheet represents a summary of a rating.
    """

    season_name = attr.ib()
    start_date = attr.ib()
    end_date = attr.ib()
    weekday_base = attr.ib()
    saturday_base = attr.ib()
    sunday_base = attr.ib()
    date_combos = attr.ib(converter=dict)

    @classmethod
    def from_records(cls, records):
        """
        Create a CheatSheet given an iterable of CalendarDate records.
        """
        date_to_garage_services = defaultdict(dict)
        day_types = {}
        for record in records:
            if not isinstance(record, CalendarDate):
                continue
            date_to_garage_services[record.date][record.garage] = record.service_key
            day_types[record.date] = record.day_type

        date_to_combos = {
            date: ExceptionCombination.from_garages(garages)
            for (date, garages) in date_to_garage_services.items()
        }

        weekday_base = cls.calculate_bases(date_to_combos, day_types, "Weekday")
        saturday_base = cls.calculate_bases(date_to_combos, day_types, "Saturday")
        sunday_base = cls.calculate_bases(date_to_combos, day_types, "Sunday")

        date_combos = {
            date: combo
            for (date, combo) in date_to_combos.items()
            if combo not in [weekday_base, saturday_base, sunday_base]
        }

        start_date = min(date_to_garage_services.keys())
        end_date = max(date_to_garage_services.keys())

        return cls(
            season_name=seasons.season_for_date(start_date),
            start_date=start_date,
            end_date=end_date,
            weekday_base=weekday_base,
            saturday_base=saturday_base,
            sunday_base=sunday_base,
            date_combos=date_combos,
        )

    @staticmethod
    def calculate_bases(date_to_combos, day_types, day_type):
        """
        Find the most commonly used combo for a given day type (Weekday, Saturday, Sunday).
        """
        dates = {date for date in day_types if day_types[date] == day_type}
        base = max(
            date_to_combos.values(),
            key=lambda combo: sum(
                1
                for date in date_to_combos
                if date in dates and date_to_combos[date] == combo
            ),
        )
        return base


@attr.s
class ExceptionCombination:
    """
    A group of services that are activated together.
    """

    service = attr.ib()
    garage_exceptions = attr.ib(converter=dict, default={})

    @classmethod
    def from_garages(cls, garages):
        """
        Build an ExceptionCombination from a {Garage => Service} dictionary.
        """
        services = set(garages.values()) - {""}
        if len(services) == 1:
            return cls(list(services)[0])

        # multiple services, find which one is the most frequent
        base_service = max(
            services,
            key=lambda service: sum(
                1 for value in garages.values() if value == service and value != ""
            ),
        )
        # then, record the others as exceptions
        exceptions = {
            service: set(
                garage for (garage, value) in garages.items() if value == service
            )
            for service in services
            if service not in {base_service, ""}
        }
        return cls(base_service, exceptions)

    def __str__(self):
        """
        Print the services and any garage exceptions.
        """
        if len(self.garage_exceptions) == 0:
            return self.service

        exceptions = ", ".join(
            f'{service} ({", ".join(sorted(garages))})'
            for (service, garages) in sorted(self.garage_exceptions.items())
        )

        return f"{self.service}, {exceptions}"


def cheat_sheet(rating):
    """
    Generate the sheet for a given rating.
    """
    return CheatSheet.from_records(rating["cal"])


def main_combine(path, file=sys.stdout):
    """
    Print the output from the cheat_sheet function.

    Optionally takes a file to write to (default: stdout)
    """
    print(cheat_sheet(Rating(path)), file=file)


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    path = args.DIR
    main_combine(path)


parser = argparse.ArgumentParser(
    description="Generate the rating cheat sheet from the HASTUS export files (post-merge)"
)
parser.add_argument("DIR", help="The Combine directory where all the files live")

if __name__ == "__main__":
    main(parser.parse_args())
