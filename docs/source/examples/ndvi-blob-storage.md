# Computing NDVI and Writing to Blob Storage

This examples computes NDVI on the most-recent Sentinel-2 Level 2A image from the Planetary Computer's STAC API.
The NDVI layer is saved as a png and COG in Azure Blob Storage.

It also demonstrates passing secrets as environment variables. To run this example, you would need to

1. Update `ndvi-job.py` to point to a Blob Storage container that you have access to
2. Create a write/write SAS token for that storage container and set it as the `SAS_TOKEN` environment variable.

We submit the script either using command-line-arguments

```{code-block} console
$ kbatch job submit --name=ndvi-job \
    --image=mcr.microsoft.com/planetary-computer/python:latest \
    --args='["python", "ndvi-blob-storage.py"]' \
    --code="ndvi-blob-storage.py" \
    --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
...
```

Or with `ndvi-blob-storage.yaml`

```{code-block} console
$ kbatch job submit -f ndvi-blob-storage.yaml --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
...
```

Notice that either way we provide the SAS Token as an environment variable.

The job configuration file:

```{literalinclude} ndvi-blob-storage.yaml
   :language: yaml
```

And the code file is

```{literalinclude} ndvi-blob-storage.py
   :language: python
```

