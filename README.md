# Registered

A set of scripts for working with TransitMaster

## Setup

```
$ asdf install
$ asdf reshim
$ pip install pipenv
$ pipenv install
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
