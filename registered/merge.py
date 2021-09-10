"""
Merge a given HASTUS export (along with the test files) into one file per type.

- NDE: stops
- PLC: places
- RTE: routes
- TRP: trips
- PAT: route patterns
- PPAT: timepoints
- BLK: blocks
- CRW: runs
"""
import argparse
import shutil
import pathlib
from datetime import datetime

MERGE_DIRECTORIES = [
    "HASTUS_export",
    "ArborTest",
    "SohamTest",
    "CabotTest",
    "BennttTest",
    "SomvlTest",
    "CharlTest",
    "AlbanTest",
    "FellsTest",
    "QuinTest",
    "LynnTest",
    "SohamDR",
]

MERGE_EXTENSIONS = ["nde", "plc", "rte", "trp", "pat", "ppat", "blk", "crw", "cal"]


def fast_merge(input_filenames, output_filename, extra=""):
    """
    Merge files.
    Replace 'dudly' with 'nubn ' since the timepoint was renamed but it's not easy to change the ID in HASTUS.
    """

    with open(output_filename, "a") as output_file:
        for input_filename in input_filenames:
            with open(input_filename) as input_file:
                output_file.write(input_file.read().replace("dudly", "nubn "))
        output_file.write(extra)


def insensitive_glob(value, prefix="*."):
    """
    Convert an extension to a case-insensitive glob.
    """
    return prefix + "".join(f"[{v.lower()}{v.upper()}]" for v in value)


def dedup_prefix(files_to_merge):
    """
    Deduplicate a list of files based on their prefix (before the dash).

    For example, given these files:
    - Prefix-11122020.blk
    - Prefix-12122020.blk
    - Other-11122020.blk

    This would return Prefix-12122020.blk and Other-11122020.blk files. These
    are the most recent files (by DDMMYYYY) for the given prefix.
    """
    most_recent_date = {}
    most_recent = {}
    for (index, filename) in enumerate(files_to_merge):
        path = pathlib.Path(filename)
        try:
            (prefix, date_str) = path.stem.rsplit("-", maxsplit=1)
        except ValueError:
            # no date suffix, ensure we include the file
            most_recent[filename] = (index, filename)
            continue
        date = datetime.strptime(date_str, "%d%m%Y").date()
        key = (prefix, path.suffix.lower())
        if key not in most_recent_date or most_recent_date[key] < date:
            most_recent_date[key] = date
            most_recent[key] = (index, filename)

    return [filename for (_, filename) in sorted(most_recent.values())]


def merge_extension(path, prefix, extension):
    """
    Merges files with the relevant extension
    """
    files_to_merge = [
        filename
        for directory in MERGE_DIRECTORIES
        for filename in sorted(
            (path / directory).glob(insensitive_glob(extension)),
            key=lambda filename: filename.name.lower(),
        )
    ]
    files_to_merge = dedup_prefix(files_to_merge)
    output_filename = path / f"{prefix}.{extension}"
    # replaces signup.blk behavior
    if extension == "blk":
        extra = (
            f"VSC;        ;          ;  ;  ;{prefix}"
            ";        ;                                        \n"
        )
    else:
        extra = ""
    fast_merge(files_to_merge, output_filename, extra)


def merge_combine(path):
    """
    Merge files with the relevant extensions in a Combine directory.
    """
    prefix = path.parent.name
    for extension in MERGE_EXTENSIONS:
        merge_extension(path, prefix, extension)


def main(args):
    """
    Entrypoint for running merge as a CLI tool.
    """
    path = pathlib.Path(args.DIR)
    if path.name.lower() != "combine":
        raise RuntimeError("expected a Combine directory")

    merge_combine(path)


parser = argparse.ArgumentParser(
    description="Merge the HASTUS export files into single file per type"
)
parser.add_argument("DIR", help="The Combine directory where all the file live")

if __name__ == "__main__":
    main(parser.parse_args())
