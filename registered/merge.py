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

MERGE_EXTENSIONS = ["nde", "plc", "rte", "trp", "pat", "ppat", "blk", "crw"]


def fast_merge(input_filenames, output_filename, extra=""):
    """
    Merge files quickly by copying the first one.
    """
    first_filename = input_filenames[0]
    shutil.copy(first_filename, output_filename)

    with open(output_filename, "a") as output_file:
        for input_filename in input_filenames[1:]:
            with open(input_filename) as input_file:
                i = iter(input_file)
                output_file.writelines(i)
        output_file.write(extra)


def insensitive_glob(value, prefix="*."):
    """
    Convert an extension to a case-insensitive glob.
    """
    return prefix + "".join(f"[{v.lower()}{v.upper()}]" for v in value)


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


def main(args):
    """
    Entrypoint for running merge as a CLI tool.
    """
    path = pathlib.Path(args.DIR)
    if path.name.lower() != "combine":
        raise RuntimeError("expected a Combine directory")

    prefix = path.parent.name
    for extension in MERGE_EXTENSIONS:
        merge_extension(path, prefix, extension)


parser = argparse.ArgumentParser(
    description="Merge the HASTUS export files into single file per type"
)
parser.add_argument("DIR", help="The Combine directory where all the file live")

if __name__ == "__main__":
    main(parser.parse_args())
