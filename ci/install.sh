#!/usr/bin/env bash
set -xe
 
pushd kbatch-proxy
python -m pip install -e .[test]
popd

pushd kbatch
python -m pip install -e .[test]
popd

pip list

set +xe