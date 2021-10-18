#!/usr/bin/env bash

wget https://raw.githubusercontent.com/microsoft/PlanetaryComputerExamples/main/datasets/sentinel-2-l2a/sentinel-2-l2a-example.ipynb

/srv/conda/envs/notebook/bin/python -m pip install papermill
# workaround https://github.com/intake/filesystem_spec/pull/784
/srv/conda/envs/notebook/bin/python -m pip uninstall gcsfs

/srv/conda/envs/notebook/bin/papermill sentinel-2-l2a-example.ipynb out.ipynb
cat out.ipynb