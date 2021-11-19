#!/usr/bin/env bash

set -eux

wget https://raw.githubusercontent.com/microsoft/PlanetaryComputerExamples/main/datasets/sentinel-2-l2a/sentinel-2-l2a-example.ipynb

/srv/conda/envs/notebook/bin/python -m pip install papermill
# workaround https://github.com/intake/filesystem_spec/pull/784
/srv/conda/envs/notebook/bin/python -m pip uninstall -y gcsfs

/srv/conda/envs/notebook/bin/papermill \
    --no-request-save-on-cell-execute \
    sentinel-2-l2a-example.ipynb \
    abs://kbatchtest.blob.core.windows.net/kbatch/output/out.ipynb?${SAS_TOKEN}