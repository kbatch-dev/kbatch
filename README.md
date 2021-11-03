# kbatch

Submit batch jobs to Kubernetes. Complements JupyterHub's support for interactive computing on Kubernetes.

This document how users can use `kbatch` to submit jobs. For documentation on setting up kbatch, see [kbatch-proxy][kbatch-proxy]

## Install

`kbatch` can be installed from source using pip:

```
$ pip install "git+https://github.com/kbatch-dev/kbatch/#egg=kbatch&subdirectory=kbatch"
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


```console
$ kbatch job submit --name=list-files \
    --command='["ls", "-lh"] \
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

```console
$ cat config.yaml
# file: config.yaml
name: "my-job"
command:
  - sh
  - script.sh
image: "mcr.microsoft.com/planetary-computer/python:latest"
code: "script.sh"

$ kbatch job submit -f config.yaml
```

Get the full help

```console
$ kbatch job submit --help
Usage: kbatch job submit [OPTIONS]

  Submit a job to run on Kubernetes.

Options:
  -n, --name TEXT        Job name.
  --image TEXT           Container image to use to execute job.
  --command TEXT         Command to execute.
  --args TEXT            Arguments to pass to the command.
  -e, --env TEXT         JSON mapping of environment variables for the job.
  -d, -description TEXT  A description of the job, optional.
  -c, --code TEXT        Local file or directory of source code to make
                         available to the job.
  -f, --file TEXT        Configuration file.
  --kbatch-url TEXT      URL to the kbatch server.
  --token TEXT           JupyterHub API token.
  --help                 Show this message and exit.
```

### List jobs


```
$ kbatch job list
...
```

### Show job details

Show the detail on a given job

```
$ kbatch job show "<job-id>
```

### Show pod logs

Note that this is the **pod** id, not the **job** id.

```
$ kbatch job logs "<pod-id>"
```

## Local file handling

Your job probably involves some local files / scripts that are used by your job. How do we get those files from your local machine to the job?

When submitting the job, you can specify the path to the local code files to make available to the job. This can be either a single file (e.g. `script.sh` or `main.py`) or a directory of files (e.g. `my-dir/`). The file will be present before your job starts up.

When you job starts executing, its working directory is `/code`. So you can safely refer to relative paths like `sh script.sh` or `python my-dir/main.py`.

## Development setup

...

## Desiderata

- **Simplicity of implementation**: https://words.yuvi.in/post/kbatch/ by Yuvi Panda captures this well.
- **Simplicity of adoption**: Users don't need to adapt their script / notebook / unit of work to the job system.
- **Integration with JupyterHub**: Runs as a JupyterHub services, uses JupyterHub for auth.
- **Runs on Kubernetes**: mainly for the simplicity of implementation, and also that's my primary use-case.

Together, these rule some great tools like [Argo workflows](https://argoproj.github.io/workflows), [Ploomber](https://github.com/ploomber/ploomber), [Elyra](https://github.com/elyra-ai/elyra). So we write our own (hopefully simple) implementation.

## Architecture

We don't want to *directly* expose the Kubernetes API to the user. At the same time, we don't want a complicated deployment with its own state to maintain. We balance these competing interests by writing a *very* simple proxy that sits between the users and the Kubernetes API. This proxy is responsible for

- Authenticating users (typically by checking the `Bearer` token with a call to the JupyterHub API)
- Authorizing the command (essentially, making sure that the API call only touches objects in the user's namespace)
- Submitting the call to the Kubernetes API, returning the results

[kbatch-proxy]: kbatch-proxy/README.md
[pangeo-docker-images]: https://github.com/pangeo-data/pangeo-docker-images
[planetary-comupter-containers]: https://github.com/microsoft/planetary-computer-containers
[YAML]: https://yaml.org/