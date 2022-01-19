# Streaming logs

```{raw} html
   <script id="asciicast-MuZYPm7ZK4Auf2yAlmdtoaOtZ" src="https://asciinema.org/a/MuZYPm7ZK4Auf2yAlmdtoaOtZ.js" async data-speed="3"></script>
```

This example submits a long-running job that prints out logs using [rich][rich].
Once the jobs is submitted, you can view the logs with `kbatch pod logs <pod-id>`,
optionally streaming them with `--stream`.

We use this job configuration file:

```{literalinclude} config.yaml
   :language: yaml
```

The job runs this shell script:

```{literalinclude} script.sh
   :language: bash
```

It's submitted with

```{code-block} console
$ kbatch job submit -f config.yaml --output=name
job_id
```

We'll use the job ID to get the pod ID

```{code-block} console
$ kbatch pod list --job-name=job_id --output=name
pod_id
```

With the pod ID, we can stream the logs

```{code-block} console
$ kbatch pod logs --job-name=job_id --stream
```


[rich]: https://rich.readthedocs.io/
