# Dask Gateway

This example demonstrates the Dask Gateway integration available on the Hub
for managing Dask clusters.

```
$ kbatch job submit --name=dask-gateway-job \
      --image=mcr.microsoft.com/planetary-computer/python:latest \
      --args='["python", "dask_gateway_example.py"]' \
      --code="dask_gateway_example.py"
```