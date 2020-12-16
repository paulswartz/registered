"""
Sync the HASTUS rating export to the TransitMaster server.

The HASTUS data is exported to \\\\HSHASTF1\\KKO. We want those files to live on
\\\\HSTMTEST01\\C$\\Ratings, along with some other directories. The basic template
is in support\\rating_template.
"""
import itertools
import argparse
import os
from pathlib import Path
import shutil
import sys
import smbclient
import smbclient.shutil
from PyInquirer import prompt
from registered import calendar, merge, parser, seasons, validate

HASTUS = "hshastf1"
TRANSITMASTER = "hstmtest01"
SLASH = "\\"


def smb_path(server, *args):
    """
    Helper function to generate an SMB path.

    >>> smb_path("server", "path", "to", "file")
    "\\\\\\\\server\\\\path\\\\to\\\\file"
    """
    return f"{SLASH}{SLASH}{server}{SLASH}{SLASH.join(args)}"


def configure_smb(args):
    """
    Configure the SMB client, prompting for username/password if needed.
    """
    username = args.username or os.environ.get("USERNAME") or os.environ.get("USER")
    password = os.environ.get("AD_PASSWORD")
    questions = []
    if not username:
        questions.append({"type": "input", "name": "username", "message": "Username:"})
    if not password:
        questions.append(
            {"type": "password", "name": "password", "message": "Password:"}
        )
    answers = {"username": username, "password": password}
    if questions != []:
        answers = {**answers, **prompt(questions)}

    smbclient.ClientConfig(username=answers["username"], password=answers["password"])


def available_hastus_exports():
    """
    Return the available HASTUS exports, sorted most-recent first.
    """
    exports = [
        export
        for export in smbclient.listdir(smb_path(HASTUS, "KKO"))
        if "AVL" in export
    ]
    return sorted(exports, key=seasons.sort_key_hastus_export, reverse=True)


def prompt_hastus_export():
    """
    Prompts the user for the HASTUS export folder to use.
    """
    questions = [
        {
            "type": "list",
            "name": "hastus_export",
            "choices": available_hastus_exports()[:10],
            "default": 0,
            "message": "Choose a HASTUS export to use:",
        }
    ]
    return prompt(questions).get("hastus_export")


def calculate_rating_folder(args):
    """
    Calculate the rating folder to use based on the HASTUS export.

    Prompts the user to confirm.
    """
    files = smbclient.listdir(smb_path(HASTUS, "KKO", args.hastus_export))
    (calendar_file,) = itertools.islice(
        (f for f in files if f.lower().endswith(".cal")), 0, 1
    )
    with smbclient.open_file(
        smb_path(HASTUS, "KKO", args.hastus_export, calendar_file)
    ) as cal_file:
        (cal_record,) = itertools.islice(parser.parse_lines(cal_file), 0, 1)
    season = seasons.season_for_date(cal_record.start_date)
    rating_folder = cal_record.start_date.strftime(f"{season}%m%d%Y")
    questions = [
        {
            "type": "input",
            "name": "folder",
            "default": rating_folder,
            "message": "Name of the rating folder?",
        }
    ]

    return prompt(questions).get("folder")


def pull_hastus_directory(args, tempdir):
    """
    Pull the HASTUS rating to the local support/ratings folder.
    """
    rating_template = Path(__file__).parent.parent / "support" / "rating_template"
    shutil.copytree(rating_template, tempdir, dirs_exist_ok=True)
    hastus_files = merge.dedup_prefix(
        smbclient.listdir(smb_path(HASTUS, "KKO", args.hastus_export))
    )
    changed = False
    for hastus_file in hastus_files:
        dst = tempdir / "Combine" / "HASTUS_export" / hastus_file
        if dst.exists():
            continue
        print(f"Pulling {hastus_file}...")
        smbclient.shutil.copy(
            smb_path(HASTUS, "KKO", args.hastus_export, hastus_file),
            tempdir / "Combine" / "HASTUS_export",
        )
        changed = True

    if changed:
        merge.merge_combine(tempdir / "Combine")

    return changed


def pull_prior_versions(tempdir):
    """
    Pull the svc-desc.txt and ANN2DEST.csv from the prior rating.
    """
    smbclient.shutil.copyfile(
        smb_path(
            "hstmcldb",
            "e$",
            "FTP_ROOT",
            "Operational Data",
            "Route Data",
            "Current_Release",
            "Routes",
            "svc-desc.txt",
        ),
        tempdir / "PriorVersions" / "svc-desc.txt",
    )
    annun_dirs = smbclient.listdir(
        smb_path(
            "hstmcldb",
            "e$",
            "FTP_ROOT",
            "Operational Data",
            "Announcements",
            "Current_Release",
        )
    )
    universal_dir = sorted(dir for dir in annun_dirs if "Universal" in dir)[0]
    smbclient.shutil.copyfile(
        smb_path(
            "hstmcldb",
            "e$",
            "FTP_ROOT",
            "Operational Data",
            "Announcements",
            "Current_Release",
            universal_dir,
            "Annundir",
            "ANN2DEST.csv",
        ),
        tempdir / "PriorVersions" / "ANN2DEST.csv",
    )


def schedules_per_garage(tempdir):
    """
    Calculate and write the schedules_per_garage.csv file in Supporting.
    """
    with open(tempdir / "Supporting" / "schedules_per_garage.csv", "w") as file:
        calendar.main_combine(tempdir / "Combine" / "HASTUS_export", file=file)


def push_directory(args, tempdir):
    """
    Push the local merged rating to the TransitMaster server.
    """
    prefix = None
    for (dirpath, dirnames, filenames) in os.walk(tempdir):
        if prefix is None:
            prefix = dirpath
        short_path = dirpath[len(prefix) + 1 :]

        if dirpath.endswith("Combine"):
            # don't traverse into subdirectories of Combine, except for HASTUS_export
            dirnames[:] = [dir for dir in dirnames if dir.lower() == "hastus_export"]

        for dirname in dirnames:
            dst = smb_path(
                TRANSITMASTER,
                "C$",
                "Ratings",
                args.rating_folder,
                short_path,
                dirname,
            )
            print(f"Making directory {dst}...")
            smbclient.makedirs(dst, exist_ok=True)
        for filename in filenames:
            if filename.startswith("."):
                continue
            src = Path(dirpath) / filename
            dst = smb_path(
                TRANSITMASTER, "C$", "Ratings", args.rating_folder, short_path, filename
            )
            print(f"Pushing {dst}...")
            smbclient.shutil.copy(str(src), dst)


def sync_hastus(args):
    """
    Given a valid list of arguments, syncs the HASTUS export data to the TM server.
    """
    tempdir = Path(__file__).parent.parent / "support" / "ratings" / args.rating_folder
    changed = pull_hastus_directory(args, tempdir)
    if not changed:
        print("No changes, nothing to do!")
        return 0

    if args.validate:
        print("Validating...")
        return_code = validate.validate_path(tempdir / "Combine")
        if return_code != 0:
            return return_code
    pull_prior_versions(tempdir)
    schedules_per_garage(tempdir)
    if args.push:
        push_directory(args, tempdir)
    return 0


def main(args):
    """
    Entrypoint for the CLI tool.
    """
    configure_smb(args)
    if args.hastus_export is None:
        args.hastus_export = prompt_hastus_export()
    if not args.hastus_export:
        return 1

    if args.rating_folder is None:
        args.rating_folder = calculate_rating_folder(args)
    if args.rating_folder is None:
        return 1

    if sync_hastus(args):
        return 0

    return 1


argparser = argparse.ArgumentParser(description="Sync the HASTUS data between servers")
argparser.add_argument(
    "--username",
    help="username to use for logging into shared drives (default: current user)",
)
argparser.add_argument("--hastus-export", help="HASTUS export directory to use")
argparser.add_argument(
    "--rating-folder",
    help="TransitMaster rating folder (default: based on HASTUS export)",
)
argparser.add_argument(
    "--no-validate",
    dest="validate",
    action="store_false",
    default=True,
    help="Skip validation of the HASTUS export",
)
argparser.add_argument(
    "--no-push",
    dest="push",
    action="store_false",
    default=True,
    help="Do not push data to the TransitMaster server",
)
if __name__ == "__main__":
    sys.exit(main(argparser.parse_args()))
