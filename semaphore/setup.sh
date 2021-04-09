#!/bin/bash
set -e

echo "Setting up semaphore..."

export PIPENV_CACHE_DIR=$SEMAPHORE_CACHE_DIR/pipenv
export ASDF_DATA_DIR=$SEMAPHORE_CACHE_DIR/.asdf
export OSMNX_CACHE_DIR=$SEMAPHORE_CACHE_DIR/osmnx
export WORKON_HOME=$SEMAPHORE_CACHE_DIR

if [[ ! -d $ASDF_DATA_DIR ]]; then
  mkdir -p $ASDF_DATA_DIR
  git clone https://github.com/asdf-vm/asdf.git $ASDF_DATA_DIR --branch v0.7.8
fi

if [[ ! -d $PIPENV_CACHE_DIR ]]; then
    mkdir -p $PIPENV_CACHE_DIR
fi

source $ASDF_DATA_DIR/asdf.sh
asdf update

asdf plugin-add python || true
asdf plugin-update --all
asdf install
pip install pip pipenv
asdf reshim python
pipenv sync -d
