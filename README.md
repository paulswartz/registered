# Registered

A set of scripts for working with TransitMaster

## Setup

### Linux/MacOS
```
$ brew install proj gdal
$ asdf install
$ asdf reshim
$ pip install pipenv
$ pipenv install  # --dev if you want to do development on the scripts
```

### Windows
```
$ choco install pyenv-win
$ pyenv install
$ pyenv rehash
$ pip install pipenv
$ pipenv install  # --dev if you want to do development on the scripts
```

## Merge

Merge a set of rating files together in the Combine directory.

Writes the merged files to `<rating>.pat`, `<rating>.nde`, &c.

```
$ pipenv run merge <path to Rating/Combine>
```

## Validate

Validate that the rating files are correct.

Exits with 1 if there were any errors.

```
$ pipenv run validate <path to Rating/Combine or Rating/Combine/HASTUS_export>
```

## Calendar

Print a CSV which has the service information for each garage, by date.

```
$ pipenv run calendar <path to Rating/Combine or Rating/Combine/HASTUS_export>
```

## Stop Comparison

Print a CSV which shows new/changed stops between two ratings.

```
$ pipenv run stop_comparison <path to current Rating/Combine> <path to next Rating/Combine>
```
