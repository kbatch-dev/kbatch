#!/usr/bin/env bash

wget https://raw.githubusercontent.com/microsoft/PlanetaryComputerExamples/main/datasets/sentinel-2-l2a/sentinel-2-l2a-example.ipynb

/srv/conda/envs/notebook/bin/jupyter nbconvert --to notebook --execute sentinel-2-l2a-example.ipynb --output out.ipynb
cat out.ipynb