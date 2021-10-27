# ndvi


```
$ kbatch job submit --name=ndvi-job \
    --image=mcr.microsoft.com/planetary-computer/python:latest \
    --command='["python", "ndvi-job.py"]' \
    --code="ndvi-job.py" \
    --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
```

Or using `job.yaml`

```console
$ kbatch job submit -f job.yaml --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
{
    'url': 'http://pcc-staging.westeurope.cloudapp.azure.com/compute/services/kbatch/jobs/2/',
    'args': ['python', 'ndvi-job.py'],
    'command': None,
    'image': 'mcr.microsoft.com/planetary-computer/python:latest',
    'name': 'ndvi-job',
    'description': None,
    'env': {'SAS_TOKEN': '***'},
    'user': 'taugspurger@microsoft.com',
    'upload': 'http://pcc-staging.westeurope.cloudapp.azure.com/compute/services/kbatch/uploads/2/'
}
```