# kbatch

> A batch-style complement to interactive workflows on JupyterHub.

`kbatch` lets you submit batch Jobs to Kubernetes. It's typically deployed as a JupyterHub service.
You might use `kbatch` if you have some long-running workflow that you want to run on the same compute
infrastructure as your JupyterHub.


```{raw} html
   <script id="asciicast-MuZYPm7ZK4Auf2yAlmdtoaOtZ" src="https://asciinema.org/a/MuZYPm7ZK4Auf2yAlmdtoaOtZ.js" async data-speed="3"></script>
```

*See the [examples gallery](examples/index.md) for more examples*

`kbatch` has two components:

1. A user-facing CLI and Python library, for users to submit Jobs
2. A proxy, `kbatch-proxy` that authorizes requests and forwards them to Kubernetes.

For user-facing documentation, stay here. Administrators looking to deploy `kbatch-proxy` can visit the [kbatch-proxy] section.

## Install

`kbatch` can be installed with Pip:

```
pip install kbatch
```

(configure)=

## Configure with JupyterHub deployment

Your Kubernetes / JupyterHub administrator might have deployed `kbatch` alongside your JupyterHub.
If this is the case, you can configure `kbatch` default URL and JupyterHub API token to use for all
of its operations.

You can generate a JupyterHub API token by logging in and visiting the token generation page, typically at `<JUPYTERHUB_URL>/hub/token`.
Provide this token in place of `<JUPYTERHUB_TOKEN>` below.

Additionally, your JupyterHub admin might have deployed `kbatch` as a [JupyterHub service][jhub-service].
If so, then you can submit jobs and make requests at the URL `<JUPYTERHUB_URL>/services/kbatch`. Use that in place of `<url-to-kbatch-server>` below.

```
$ kbatch configure --kbatch-url="https://<url-to-kbatch-server>" --token="<JUPYTERHUB_TOKEN>"
```

This will create configuration file that specifies the default URL and credentials to use for all `kbatch` operations.

## Next steps

For more on how to use `kbatch`, see the [User guide](./user-guide.md)

[kbatch-proxy]: kbatch-proxy.md
[jhub-service]: https://z2jh.jupyter.org/en/latest/administrator/services.html

```{toctree}
user-guide
examples/index.md
kbatch-proxy
dev-guide
```
