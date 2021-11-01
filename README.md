# kbatch

Submit batch jobs to JupyterHub.

*also*

An asynchronous / batch complement to what JupyterHub already provides.

## Desiderata

- **Simplicity of implementation**: https://words.yuvi.in/post/kbatch/ by Yuvi Panda captures this well.
- **Simplicity of use**: Ideally users don't need to adapt their script / notebook / unit of work to the job system.
- **Integration with JupyterHub**: Runs as a JupyterHub services, uses JupyterHub for auth, etc.
- **Runs on Kubernetes**: mainly for the simplicity of implementation, and also that's my primary use-case.

Together, these rule some great tools like [Argo workflows](https://argoproj.github.io/workflows), [Ploomber](https://github.com/ploomber/ploomber), [Elyra](https://github.com/elyra-ai/elyra). So we write our own (hopefully simple) implementation.

## Architecture

We don't want to *directly* expose the Kubernetes API to the user. At the same time, we don't want a complicated deployment with its own state to maintain. We balance these competing interests by writing a *very* simple proxy that sits between the users and the Kubernetes API. This proxy is responsible for

- Authenticating users (typically by checking the `Bearer` token with a call to the JupyterHub API)
- Authorizing the command (essentially, making sure that the API call only touches objects in the user's namespace)
- Submitting the call to the Kubernetes API, returning the results

## Usage (hypothetical)

Authenticate with the server

```
$ kbatch login https://url-to-kbatch-server
```

This will create configuration file that specifies the default URL and credentials to use for all `kbatch` operations.

Submit a job

```console
$ kbatch job submit --name=test \
    --image="mcr.microsoft.com/planetary-computer/python" \
    --command="[\"sh\"]" \
    --file=examples/script.sh \
    --url="http://localhost:8000/services/kbatch/" \
    --env='{"SAS_TOKEN": "'${SAS_TOKEN}'"}'
{
    'url': 'http://localhost:8000/services/kbatch/jobs/14/',
    'command': ['sh'],
    'image': 'mcr.microsoft.com/planetary-computer/python',
    'name': 'test',
    'env': {'SAS_TOKEN': '***'},
    'user': 'taugspurger',
    'upload': 'http://localhost:8000/services/kbatch/uploads/19/'
}
```

List jobs

```
$ kbatch jobs list
...
```

Show the detail on a given job

```
$ kbatch jobs show --job-id=...
```

## Local file handling

Your job probably involves some local files / scripts that are used by your job. How do we get those files from your local machine to the job?

When submitting the job, you can specify the path to the local code files to make available to the job. This can be either a single file (e.g. `script.sh` or `main.py`) or a directory of files (e.g. `my-dir/`). The file or files are then uploaded to the server. That gets us from local to "the cloud". Now we need to complete the last step from the cloud to the job.

*Before* your job starts up, the server ensures that your local files are available on the file system running your job. By default, your code is available at `/code`. If you uploaded a single script `script.sh`, that will be available at `/code/script.sh`.

If you uploaded a directory of files named `my-dir`, it's available at `/code/<my-dir>/`.

When you job starts executing, its working directory is `/code`. So you can safely refer to relative paths like `sh script.sh` or `python my-dir/main.py`.

## Development setup

This setup assumes you have docker installed and have cloned the repository.

```
$ # from the root of the git repo
$ cd kbatch-server/docker-local
$ docker-compose up
```

That starts up JupyterHub and kbatch-server. Next, generate a token by visiting http://localhost:8000/hub/token, using any username / password, and requesting a token. We'll use that in the next section.

Open up a new terminal, create and activate some kind of virtual environment, and install the dependencies

```
$ cd kbatch
$ python -m pip install -e .
```

Now you should have the `kbatch` CLI on your path.

```
$ kbatch configure --kbatch-url=http://localhost:8050/services/kbatch --jupyterhub-url=http://localhost:8000/hub/api --token="<token from earlier>
Wrote config to <config-dir>/kbatch/config.json
```

Now you can submit jobs.

```
kbatch job submit --name=my-job \
    --image=mcr.microsoft.com/planetary-computer/python:latest \
    --command='["python", "-c", "print(1)"]'
```