# Registered

A set of scripts for working with TransitMaster. Reference the rating process documentation [here](https://github.com/mbta/wiki/blob/master/transit_tech/Procedures/TransitMaster/TM-03_Make_Updates.md).

**Effect:**	Different steps throughout the rating process. Allows data validation before importing into TransitMaster.
**Circumstances:**	As needed. Generally once per quarterly rating.
**Required Skills:**	None
**Required Tools:**	VPN access, a text editor, access to TM databases

## Setup

Reminder: Before the set-up process, clone the registered repository and make sure you're working within it.

### Linux/MacOS
```
$ brew install freetds gdal freetds
$ asdf install
$ asdf reshim
$ pip install pipenv
$ pipenv sync  # --dev if you want to do development on the scripts
$ cp .env.template .env
$ vi .env  # configure environment variable
```

### Windows
```
$ choco install pyenv-win
$ pyenv install 3.9.20
$ pyenv rehash
$ pip install pipenv
$ pipenv sync  # --dev if you want to do development on the scripts
$ copy .env.template .env
$ wordpad .env  # configure environment variable
```

## HASTUS sync

Sync a HASTUS export to the TransitMaster server, validating the data in the process.

- Writes the data to `support/ratings/*` for later processing if needed.
- Will prompt for your AD password, or you can put it in the `AD_PASSWORD` environment
  variable. If you have trouble logging in, set `USERNAME` to your AD account.

```
$ pipenv run hastus_sync # (if testing, use "—no-push" to avoid actually updating the rating data on the TM server)
```

## Scripts

For the scripts below, you will have to access the rating folder on <TRANSITMASTER_FILE_SERVER> on your local machine to direct it to the right path. If you're working from a PC computer, you are all set. If you're working from a MAC, follow the instructions below.

### Linux/MacOS
- From your MAC, open finder
- Click 'Go'
- Click 'Connect to Server'
- Type 'smb://<TRANSITMASTER_FILE_SERVER>/c$/Ratings'
- Access the files at '/Volumes/Ratings/[Rating]' (i.e. /Volumes/Ratings/Winter12202020)


## Merge

Merge a set of rating files together in the Combine directory. This step is found under TM-03.05, step 2 in [TransitMaster New Rating Procedure]

Writes the merged files to `<rating>.pat`, `<rating>.nde`, &c.

```
$ pipenv run merge <path to Rating/Combine>
```

## Validate

Validate that the rating files are correct. This step is found under TM-03.05, step 4 (Integrity Checker) in [TransitMaster New Rating Procedure]

Exits with 1 if there were any errors.

```
$ pipenv run validate <path to Rating/Combine or Rating/Combine/HASTUS_export>
```

## Calendar

Print a CSV which has the service information for each garage, by date. This step is meant to help facilitate TM-03.05, step 7 in [TransitMaster New Rating Procedure]

```
$ pipenv run calendar <path to Rating/Combine/HASTUS_export>
```

## Cheat Sheet

Print a summary of the relevant dates/services for the rating.

```
$ pipenv run cheat_sheet <path to Rating/Combine/HASTUS_export>
```

## Stop Comparison

Print a CSV which shows new/changed stops between two ratings. This step is found under TM-03.06, step 1 in [TransitMaster New Rating Procedure]

1. Copy .env.template to .env and fill out at least the following variables with the TransitMaster DB server information from 1Password.
    - `TRANSITMASTER_DATABASE_SERVER`
    - `TRANSITMASTER_UID`
    - `TRANSITMASTER_PWD`

```
$ pipenv run stop_comparison <path to current Rating/Combine> <path to next Rating/Combine>
```

## Missing/Stop Intervals

Writes an HTML file showing calculated distance/direction intervals which are not in the TransitMaster database.

This step is found under TM-03.06, step 2 in [TransitMaster New Rating Procedure]

1. Copy .env.template to .env and fill out at least the following variables with the TransitMaster DB server information from 1Password.
    - `TRANSITMASTER_DATABASE_SERVER`
    - `TRANSITMASTER_UID`
    - `TRANSITMASTER_PWD`

```
$ pipenv run missing_intervals intervals.html
```

And then open `intervals.html` in your browser.

For stop intervals:

```
$ pipenv run stop_intervals intervals.html --stop-id=32549
```

[TransitMaster New Rating Procedure]: https://github.com/mbta/wiki/blob/master/transit_tech/Procedures/TransitMaster/TM-03_Make_Updates.md
