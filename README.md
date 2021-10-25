# kbatch

Submit batch jobs to JupyterHub.

*also*

An asynchronous / batch complement to what JupyterHub already provides.

## Desiderata

- **Simplicity of implementation**: https://words.yuvi.in/post/kbatch/ by Yuvi Panda captures this well.
- **Simplicity of use**: Ideally users don't need to adapt their script / notebook / unit of work to the job system.
- **Integration with JupyterHub**: Runs as a JupyterHub services, uses JupyterHub for auth, etc.
- **Runs on Kubernetes**: mainly for the simplicity of implementation, and also that's my primary use-case.
- **Users do not have access to the Kubernetes API**: partly because if users need to know about Kubernetes then we've failed, and partly for security.

Together, these rule some great tools like [Argo workflows](https://argoproj.github.io/workflows), [Ploomber](https://github.com/ploomber/ploomber), [Elyra](https://github.com/elyra-ai/elyra). So we write our own (hopefully simple) implementation.

## Architecture

Because end-users don't have access to the Kubernetes API, we have a client/server model. Users make API requests to the server to submit / list / show jobs.

The server is split into two parts: a frontend that handles requests, and a backend that submits them to Kubernetes.

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