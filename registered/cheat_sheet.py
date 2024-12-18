"""
CLI tool to output the rating cheat sheet.

The cheat sheet has the following info:

- name of the rating (Winter 2021)
- start date (first date the rating is active)
- end date (last date the rating is active)
- base schedules (Weekday, Saturday, Sunday, and any garage-level exceptions)
- dates with exception combinations (incl. garage if needed)
- weekday + test/dead reckoning (ST1 DR1) on the first weekday labeled TAKE THIS OUT
- any Level 3 / Level 4 tags labeled TAKE THIS OUT

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
from datetime import timedelta
import itertools
import operator
import attr
from registered.rating import Rating
from registered.parser import CalendarDate
from registered import seasons

(DATE_RANGE_FORMAT, DATE_FORMAT) = {
    "darwin": ("%a %-m/%-d/%Y", "%a %-m/%-d"),
    "linux": ("%a %-m/%-d/%Y", "%a %-m/%-d"),
    "win32": ("%a %#m/%#d/%Y", "%a %#m/%#d"),
}[sys.platform]


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

    def __str__(self):
        # get the first weekday to apply the DR1/ST1 combos
        first_weekday = self.start_date
        while first_weekday < self.end_date:
            if first_weekday.weekday() < 5:  # weekday
                if first_weekday not in self.date_combos:  # not already overridden
                    break
            first_weekday += timedelta(days=1)

        date_combos = list(self.date_combos.items())
        date_combos.append(
            (first_weekday, f"{str(self.weekday_base)} DR1 ST1 *** TAKE THIS OUT")
        )
        date_combos.sort()
        exceptions = []
        for combo, date_group in itertools.groupby(
            date_combos, key=operator.itemgetter(1)
        ):
            dates = {date for (date, _) in date_group}
            for group in date_groups(dates):
                min_date = min(group)
                if len(group) == 1:
                    exceptions.append(f"{min_date.strftime(DATE_FORMAT)} {str(combo)}")
                else:
                    max_date = max(group)
                    exceptions.append(
                        min_date.strftime(DATE_FORMAT)
                        + " - "
                        + max_date.strftime(DATE_FORMAT)
                        + " "
                        + str(combo)
                    )

        exceptions = "\n".join(exceptions)

        return f"""\
{self.season_name} {self.end_date.year}

{self.start_date.strftime(DATE_RANGE_FORMAT)} - {self.end_date.strftime(DATE_RANGE_FORMAT)}

Weekday {str(self.weekday_base)}
Saturday {str(self.saturday_base)}
Sunday {str(self.sunday_base)}

{exceptions}
"""

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
            if record.service_key == "":
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
                if date in dates
                and date_to_combos[date] == combo
                and not combo.should_take_out()
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
        suffix = ""
        if self.should_take_out():
            suffix = " *** TAKE THIS OUT"
        if len(self.garage_exceptions) == 0:
            return self.service + suffix

        exceptions = ", ".join(
            f'{service} ({", ".join(sorted(garages))})'
            for (service, garages) in sorted(self.garage_exceptions.items())
        )

        return f"{self.service}, {exceptions}{suffix}"

    def service_keys(self):
        """
        Return a set of all service keys used by this combo.
        """
        return set(self.garage_exceptions.keys()) | {self.service}

    def should_take_out(self):
        """
        Return true if a given combination should be removed from TransitMaster during the import.

        - Level 3 or 4 service
        - Weather-related services
        """
        return any(
            True
            for service in self.service_keys()
            if service.lower()[1] in {"3", "4"}
            or service.lower()[:2] in {"we", "wt", "wn"}
        )


def date_groups(dates):
    """
    Given an iterable of dates, group them into adjacent sets.
    """
    groups = []
    current_group = None
    last_date = None
    for date in sorted(dates):
        if last_date is None:
            current_group = {date}
            last_date = date
            continue

        if date - last_date == timedelta(days=1):
            # adjacent to last date
            last_date = date
            current_group.add(date)
            continue

        # not adjacent, start a new group
        groups.append(current_group)
        current_group = {date}
        last_date = date

    groups.append(current_group)
    return groups


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
    description="Generate the rating cheat sheet from the HASTUS export files"
)
parser.add_argument("DIR", help="The HASTUS_export directory where all the files live")

if __name__ == "__main__":
    main(parser.parse_args())
