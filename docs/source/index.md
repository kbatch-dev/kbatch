# kbatch

> A batch-style complement to interactive workflows on JupyterHub.

`kbatch` lets you submit batch Jobs to Kubernetes. It's typically deployed as a JupyterHub service.
You might use `kbatch` if you have some long-running workflow.

`kbatch` has two components:

1. A user-facing CLI and Python library, for users to submit Jobs
2. A proxy, `kbatch-proxy` that authorizes requests and forwards them to Kubernetes.

For user-facing documentation, stay here. Administrators looking to deploy `kbatch-proxy` can visit the [kbatch-proxy] section.

## Install

`kbatch` can be installed with Pip:

```
pip install kbatch
```

## Usage

`kbatch` is typically uses JupyterHub for authentication, so you'll first need an API token. You can generate one by logging in and visiting the token generation page, typically at `<JUPYTERHUB_URL>/hub/token`. Provide this token in place of `<JUPYTERHUB_TOKEN>` below:

```
$ kbatch configure --kbatch-url="https://url-to-kbatch-server" --token="<JUPYTERHUB_TOKEN>"
```

This will create configuration file that specifies the default URL and credentials to use for all `kbatch` operations.

### Submit a job

At a minimum, jobs require

1. A `name` to identify the job.
2. A `command` to run, as a list of strings (e.g. `["ls"]` or `["papermill", "my-notebook.ipynb"]`).
3. A container `image` to use (consider matching the one used on your Hub, perhaps one from [pangeo-docker-images] or [planetary-computer-containers])


```{code-block} console
$ kbatch job submit --name=list-files \
    --command='["ls", "-lh"]' \
    --image=alpine
```

Additionally, you can provide code (either a directory or a single file) to make available on the server
for your Job.

```console
$ kbatch job submit --name=test \
    --image="mcr.microsoft.com/planetary-computer/python" \
    --command='["papermill", "notebook.ipynb"]' \
    --file=notebook.ipynb
```

Rather than providing all those arguments on the command-line, you can create a [YAML] configuration file.

```yaml
# file: config.yaml
name: "my-job"
command:
  - sh
  - script.sh
image: "mcr.microsoft.com/planetary-computer/python:latest"
code: "script.sh"
```

And provide it lie

```console
$ kbatch job submit -f config.yaml
```

Get the full help

```{click} kbatch.cli:cli
---
prog: kbatch
---
```

[kbatch-proxy]: kbatch-proxy.md

```{toctree}
kbatch-proxy
```