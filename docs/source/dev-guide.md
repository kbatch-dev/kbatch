# Dev Guide

## Development setup

Clone the `kbatch` repo onto your local machine and create a virtual environment (`conda`, `venv`, etc.) with Python 3.9 installed. From this directory, you can pip install the packages needed for development

```
$ pip install -e ./kbatch[all]
...
$ pip install -e ./kbatch-proxy[all]
```

> NOTE: The `-e` signifies that this is an "editable install", read more [here](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs).

The first pip install command above should've also installed `pre-commit` which is used to format and lint the code. Run the following command to start using `pre-commit`

```
$ pre-commit install --install-hooks
```

### Run `pytest`

To validate your changes against the test suite, run

```
$ pytest -v ./kbatch
...
$ pytest -v ./kbatch-proxy
```

### Run `mypy`

To perform `mypy` type checking, run

```
pre-commit run mypy --all-files
```

### To build the docs locally

To build the docs locally, run

```
$ cd ./docs
$ make html
```


## `kbatch-proxy` development setup

We don't have a fully working docker-ized setup, since we (i.e. Tom) don't know how to do Kubernetes within docker. So the current setup relies on

1. k3d for Kubernetes
2. JupyterHub as a regular Python process
3. kbatch-proxy as a regular Python process

### Create a cluster

```
$ k3d cluster create kbatch
```

### Create a Hub

make sure to `npm install configurable-http-proxy`.

```
$ cd hub
$ jupyterhub
```

### Start kbatch-proxy

```
KBATCH_PREFIX=/services/kbatch \
  KBATCH_PROFILE_FILE=tests/profile_template.yaml \
  JUPYTERHUB_API_TOKEN=super-secret \
  JUPYTERHUB_API_URL=http://127.0.0.1:8000/hub/api \
  JUPYTERHUB_HOST=http://127.0.0.1:8000 \
  uvicorn kbatch_proxy.main:app --reload --port=8050
```

You'll might want to log in and create a token at http://localhost:8000/hub/token. The `kbatch configure` with that token.

## Release process

These are the current steps that it takes to cut a new release of `kbatch`.

### Release new version of `kbatch`/`kbatch-proxy`:

1. Update any relevant docs via pull request
2. tag a new (PEP440) version with `tbump`:
   ```
   tbump NEW_VERSION # e.g. tbump 0.5.0a1
   ```
3. [Draft a release on the `kbatch` GitHub repo](https://github.com/kbatch-dev/kbatch/releases), referencing the tag just created.
   - This triggers the [`publish-image.yaml`](https://github.com/kbatch-dev/kbatch/blob/main/.github/workflows/publish-image.yaml) workflow which:
     - publishes a container image for `kbatch-proxy` to the [GitHub container registry](https://github.com/kbatch-dev/kbatch/pkgs/container/kbatch-proxy).
     - publish `kbatch` and `kbatch-proxy` python libraries to PyPI.

#### Update appVersion in helm chart

Once the image is published, you can bump the version of kbatch-proxy in the helm chart to match.
This is stored in `appVersion` in [kbatch/Chart.yaml](https://github.com/kbatch-dev/helm-chart/blob/HEAD/kbatch/Chart.yaml)
and `kbatch_version` in [chartpress.yaml](https://github.com/kbatch-dev/helm-chart/blob/main/chartpress.yaml).
Updating appVersion _probably_ means a chart release is in order, but not necessarily.

### Release new version of `helm-chart`:

The helm chart version and kbatch version are versioned separately,
though their versions may be the same or similar.
The latest version of the chart should probably reference the latest version of kbatch-proxy,
but chart releases can be made without needing updates to the Python packages if there are changes to the chart labels, options, etc.

1. make sure the `appVersion` is up to date in Chart.yaml and in sync with `kbatch_version` in chartpress.yaml.
2. Update any relevant docs and merge these changes into the codebase.
3. [Draft a release on the `helm-chart` GitHub repo](https://github.com/kbatch-dev/helm-chart/releases), creating a new tag.
   - This triggers the [`publish-chart.yaml`](https://github.com/kbatch-dev/helm-chart/blob/main/.github/workflows/publish-charts.yml) workflow which:
     - publishes a Helm chart to the [GitHub Pages site](https://kbatch-dev.github.io/helm-chart/) for this repo.

Note about prereleases: helm has strict semver requirements, so prerelease tags on the helm chart should look like e.g. `0.5.0-alpha.1`,
while the Python packages use pep440 so the same version would be `0.5.0a1` for `kbatch` itself.
This is what would appear in the chart's `appVersion`.

