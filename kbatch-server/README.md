# kbatch-server

The server component of kbatch.

## Configuration

Running the application requires setting several configuration values.

Set this in a `.env` file

|       Settings key        |                                          Purpose                                          |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| JUPYTERHUB_API_TOKEN      | Authenticate with JupyterHub                                                              |
| JUPYTERHUB_SERVICE_PREFIX | The prefix this application is running under as a JupyterHub service                      |
| DEFAULT_FILE_STORAGE      | The file storage class to use for user-uploaded scripts. Must be accessible by Kubernetes |
| AZURE_ACCOUNT_NAME        | Specific to `storage.backends.azure_storage.AzureStorage`                                 |
| AZURE_CONTAINER           | Specific to `storage.backends.azure_storage.AzureStorage`                                 |
| AZURE_SAS_TOKEN           | Specific to `storage.backends.azure_storage.AzureStorage`                                 |

## Upload storage

kbatch allows users to upload code and the backend takes care of making it available to the pod at job runtime.
We implement this by

1. Providing an `uploads/` endpoint where users can `POST` ZIP archives with code
2. Making an HTTP request from the Job's init container to fetch and unzip the code

This of course requires a storage backend that can (securely) provide access to the files. Right now
we're using the [azure storage](https://django-storages.readthedocs.io/en/latest/backends/azure.html) backend from
`django-storages`. We might consider (optionally) folding this into the service it self.

## Deployment

The application can be deployed with helm. Given a configuration like the following

```
# config.yaml
app:
  jupyterhub_api_token: "<secret-token>"
  jupyterhub_api_url: https://pcc-staging.westeurope.cloudapp.azure.com/compute/hub/api
  job_namespace: staging
  service_prefix: "/compute/services/kbatch"
  service:
    type: LoadBalancer
    annotations:
      service.beta.kubernetes.io/azure-dns-label-name: kbatch-staging
```

Deploy with with

```
$ helm upgrade --install kbatch-server ./helm/kbatch-server -f config.yaml -n staging
```

Note that this requires the JupyterHub to be configured with a `kbatch` service.

```
# file: jupyterhub_config.yaml
jupyterhub:
  hub:
    services:
      kbatch:
        admin: true
        api_token: "<secret-token>"
        url: "http://kbatch-staging.westeurope.cloudapp.azure.com"
```

Make sure that the service has admin access, that the API token matches, and that the URLs all line up.

## Testing

The `.env.test` file contains settings for unit tests. You should have kubernetes configured independently.

```
$ KBATCH_SETTINGS_PATH=.env.test pytest
```