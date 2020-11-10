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
