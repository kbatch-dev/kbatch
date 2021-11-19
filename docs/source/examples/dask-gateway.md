# Dask Gateway Example

This example shows how to start and manage a Dask cluster on a hub that is deployed with [Dask Gateway][gateway].

It uses the [Microsoft Planetary Computer Hub][pc], but should work on any Hub with Dask Gateway.

We use this job configuration file:

```{literalinclude} dask-gateway-job.yaml
   :language: yaml
```

The job runs this python file:

```{literalinclude} dask-gateway.py
   :language: python
```

And is submitted with

```{code-block} console
$ kbatch job submit -f dask-gateway-job.yaml
```

[pc]: https://planetarycomputer.microsoft.com/
[gateway]: https://gateway.dask.org/