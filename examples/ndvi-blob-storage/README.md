# ndvi

Demonstrates ...


```
$ kbatch job submit --name=ndvi-job \
    --image=mcr.microsoft.com/planetary-computer/python:latest \
    --command='["python", "ndvi-job.py"]' \
    --code="ndvi-job.py" \
    --env="{\"SAS_TOKEN\": \"$SAS_TOKEN\"}"
```