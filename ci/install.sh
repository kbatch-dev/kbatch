#!/usr/bin/env bash
set -xe
 
pushd kbatch-server
python -m pip install -e .[test]
popd

pushd kbatch
python -m pip install -e .[test]
popd

pip list

set +xe