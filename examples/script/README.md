# Submit a script

This example submits a script. You can customize the job using a YAML file:

```
$ kbatch job submit --file=job.yaml \
  --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
```

or arguments to the CLI

```
$ kbatch job submit --name=my-job \
  --image=mcr.microsoft.com/planetary-computer/python:latest \
  --command='["sh", "script.sh"]' \
  --code="script.sh" \
  --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
{
    'url': 'http://localhost:8000/services/kbatch/jobs/5/',
    'command': ['sh', 'script.sh'],
    'image': 'mcr.microsoft.com/planetary-computer/python:latest',
    'name': 'my-job',
    'description': None,
    'env': None,
    'user': 'taugspurger',
    'upload': 'http://localhost:8000/services/kbatch/uploads/5/'
}  
```




