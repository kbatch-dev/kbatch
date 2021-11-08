# kbatch-proxy

`kbatch-proxy` is the server component of the `kbatch` system. This section is relevant for Kubernetes / JupyterHub administrators looking to install `kbatch` for their users. Users should visit the [User guide](/user-guide.md) for more on how to use `kbatch`.

See <https://kbatch-dev.github.io/helm-chart/> for instructions on installing `kbatch` with helm.

You might want to install `kbatch` as a [JupyterHub service][jhub-service].

```{code-block} yaml
# file: jupyterhub-config.yaml
hub:
  services:
    kbatch:
      url: "<kbatch-url>"
      api_token: "<JUPYTERHUB_API_TOKEN>"  # generate with openssl rand -hex 32
      admin: true
```

[jhub-service]: https://z2jh.jupyter.org/en/latest/administrator/services.html