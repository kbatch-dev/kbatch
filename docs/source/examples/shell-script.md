# Submit a script

This example submits a shell script. It installs a few additional libraries, downloads a notebook from GitHub,
and executes it with [papermill][papermill].

It requires a SAS token to upload the executed notebook to Azure Blob Storage, which is provided as an environment variable.
You can customize the job using a YAML file:

```{code-block} console
$ kbatch job submit --file=shell-script.yaml --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
...
```

or arguments to the CLI

```{code-block} console
$ kbatch job submit --name=my-job \
  --image=mcr.microsoft.com/planetary-computer/python:latest \
  --command='["sh", "shell-script.sh"]' \
  --code="shell-script.sh" \
  --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
...
```

The job configuration file:

```{literalinclude} shell-script.yaml
   :language: yaml
```

And the code file is

```{literalinclude} shell-script.sh
   :language: bash
```




[papermill]: https://papermill.readthedocs.io/en/latest/