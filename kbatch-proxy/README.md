# kbatch-proxy

A simple Kubernetes proxy, allowing JupyterHub users to make requests to the Kubernetes API without having direct access to the Kubernetes API.

## Motivation

We want `kbatch` users to be able to create Kubernetes Jobs, access logs, etc., but

1. Don't want to grant them *direct* access to the Kubernetes API
2. Don't want to maintain a separate web application, with any state that's independent of Kubernetes

Enter `kbatch-proxy`

## Design

A simple FastAPI application that sits in between `kbatch` users and the Kubernetes API. It's expected that the `kbatch-proxy`
application has access to the Kubernetes API, with permission to create namespaces, jobs, etc. This will often be run as a JupyterHub service.

Users will make requests to `kbatch-proxy`. Upon request we will

1. Validate that the user is authenticated with JupyterHub (checking the `Bearer` token)
2. Validate that data the user is submitting or requesting meets our [security model](#security-model)
3. Make the request to the Kubernetes API on behalf of the user

## Security model

This remains to be proven effective, but the hope is to let users do whatever they want in their own namespace and nothing outside of their namespace.

## Container images

We provide container images at <https://github.com/kbatch-dev/kbatch/pkgs/container/kbatch-proxy>.

```
$ docker pull ghcr.io/kbatch-dev/kbatch-proxy:latest
```

## Deployment

`kbatch-proxy` is most easily deployed as a JupyterHub service using Helm. A few values need to be configured:

```yaml
# file: config.yaml
app:
  jupyterhub_api_token: "<jupyterhub-api-token>"
  jupyterhub_api_url: "https://<jupyterhub-url>/hub/api/"
  extra_env:
    KBATCH_PREFIX: "/services/kbatch"

# image:
#   tag: "0.1.4"  # you likely want to pin the latest here.
```

Note: we don't currently publish a helm chart, so you have to `git clone` the kbatch repository.

From the `kbatch/kbatch-proxy` directory, use helm to install the chart

```
$ helm upgrade --install kbatch-proxy ../helm/kbatch-proxy/ \
    -n "<namepsace> \
    -f config.yaml
```

You'll need to configure kbatch as a JupyterHub service. This example makes it available at `/services/kbatch` (this should match `KBATCH_PREFIX` above):

```yaml
jupyterhub:
  hub:
    services:
      kbatch:
        admin: true
        api_token: "<jupyterhub-api-token>"  # match the api token above
        url: "http://kbatch-proxy.<kbatch-namespace>.svc.cluster.local"
```

That example relies on kbatch being deployed to the same Kubernetes cluster as JupyterHub, so JupyterHub can proxy requests to `kbatch-proxy` using Kubernetes' internal DNS. The namespace in that URL should match the namespace where `kbatch` was deployed.

## Dask Gateway Integration

If your JupyterHub is deployed with Dask Gateway, you might want to set a few additional environment variables in the job
so that they behave similarly to the singleuser notebook pod.

```yaml
app:
  extra_env:
    KBATCH_JOB_EXTRA_ENV: |
      {
        "DASK_GATEWAY__AUTH__TYPE": "jupyterhub",
        "DASK_GATEWAY__CLUSTER__OPTIONS__IMAGE": "{JUPYTER_IMAGE_SPEC}",
        "DASK_GATEWAY__ADDRESS":  "https://<JUPYTERHUB_URL>/services/dask-gateway",
        "DASK_GATEWAY__PROXY_ADDRESS": "gateway://<DASK_GATEWAY_ADDRESS>:80"
      }

```

## Development setup

We don't have a fully working docker-ized setup, since we (i.e. Tom) don't know how to do Kubernetes within docker. So the current setup relies on

1. k3d for Kubernetes
2. JupyterHub as a regular Python process
3. kbatch-proxy as a regular Python process

### Create a cluster

```
$ k3d cluster create ksubmit
```

### Create a Hub

make sure to `npm install` configurable-http-proxy.

```
$ cd hub
$ jupyterhub
```

### Start kbatch-proxy

```
KBATCH_PREFIX=/services/kbatch \
  KBATCH_PROFILE_FILE=tests/profile_template.yaml \
  JUPYTERHUB_API_TOKEN=super-secret \
  JUPYTERHUB_API_URL=http://127.0.0.1:8000/hub/api \
  JUPYTERHUB_HOST=http://127.0.0.1:8000 \
  uvicorn kbatch_proxy.main:app --reload --port=8050
```

You'll might want to log in and create a token at http://localhost:8000/hub/token. The `kbatch configure` with that token.