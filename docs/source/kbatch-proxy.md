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

## Job customization

Administrators will likely want to customize the jobs that are submitted by users. For example,
they might want to control the nodes that jobs are scheduled on by setting a node affinity.

This is most easily accomplished with a "job-template-file". The Job template itself can be
embedded in the helm configuration. You should set two variables:

1. `kbatch-proxy.app.extraenv.KBATCH_JOB_TEMPLATE_FILE`: The filepath to store the job template.
2. `kbatch-proxy.app.extraFiles`: The YAML configuration to merge with pods.

Note that the `mountPath` in the job template should match the value at `KBATCH_JOB_TEMPLATE_FILE`.


```yaml
# file: kbatch-config.yaml
kbatch-proxy:
  app:
    # jupyterhub_api_token, jupyterhub_api_url set by terraform
    extra_env:
      KBATCH_JOB_TEMPLATE_FILE: /job-template.yaml
    extraFiles:
      job_template:
        mountPath: /job-template.yaml
        data:
          apiVersion: batch/v1
          kind: Job
          spec:
            template:
              spec:
                tolerations:
                  - effect: NoSchedule
                    key: hub.jupyter.org/dedicated
                    operator: Equal
                    value: user
                  - effect: NoSchedule
                    key: hub.jupyter.org_dedicated
                    operator: Equal
                    value: user
                affinity:
                  nodeAffinity:
                    requiredDuringSchedulingIgnoredDuringExecution:
                      nodeSelectorTerms:
                        - matchExpressions:
                          - key: hub.jupyter.org/node-purpose
                            operator: In
                            values:
                              - user
```

## Namespace customization

```{versionadded} 0.5
```

The `kbatch_namespace_manifests_file` setting can point to a yaml file containing any number of kubernetes manifests to create within a given kbatch namespace.
This allows creation of ResourceQuotas, NetworkPolicies, and other per-namespace resources you might want to have in every user namespace.
The manifests are created using kubernetes [server-side apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/).

For example, the resource quota:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: mem-cpu-demo
spec:
  hard:
    count.pods: "10"
    requests.cpu: "5"
    requests.memory: 5Gi
    limits.cpu: "20"
    limits.memory: 20Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Egress
  - Ingress
```

would limit the number of pods in _each_ kbatch namespace to 10,
limit resource requests and limits, and deny _all_ network traffic into and out of the namespace.
so jobs would not have permission to access the network.

[jhub-service]: https://z2jh.jupyter.org/en/latest/administrator/services.html
