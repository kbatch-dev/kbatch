"""
Build and submit Jobs to Kubernetes.

This is used only by the kbatch backend. kbatch users do not have access to the Kubernetes API.
"""
import asyncio
import collections.abc
import functools
import pathlib
import string
import escapism
import uuid
from typing import Dict, Tuple, Optional, List, Union, Mapping, Any

from kubernetes import client
from kubernetes import config
from kubernetes.client.models import (
    V1Job,
    V1JobSpec,
    V1PodSpec,
    V1PodTemplateSpec,
    V1ObjectMeta,
    V1Volume,
    V1VolumeMount,
    V1ConfigMap,
    V1ConfigMapVolumeSource,
    V1KeyToPath,
    V1Toleration,
    V1ResourceRequirements,
    V1EnvVar,
    V1Container,
)

from .models import Job

# TODO: figure out how to associate with a user. Attach it as a label  or annotation probably.
# TODO: figure out how to "upload" files.
# TODO: get job logs, cache to storage, delete pods
# TODO: clean up jobs
# TODO: Insert env vars for Dask Gateawy (JUPYTERHUB_API_TOKEN, auth, image, proxy, etc.)

SAFE_CHARS = set(string.ascii_lowercase + string.digits)


def parse_toleration(t: str) -> V1Toleration:
    if t.count("=") == 1 and t.count(":") == 1:
        key, rest = t.split("=", 1)
        value, effect = rest.split(":", 1)
        return V1Toleration(key=key, value=value, effect=effect)
    else:
        raise ValueError(
            f"Invalid toleration {t}. Should be of the form <key>=<value>:<effect>"
        )


def make_job(
    job: Job,
    *,
    namespace: str = "default",
    labels: Optional[Mapping[str, str]] = None,
    annotations: Dict[str, str] = None,
    script: str = None,
    cpu_guarantee: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    mem_limit: Optional[str] = None,
    mem_guarantee: Optional[str] = None,
    extra_resource_limits: Optional[Dict[str, str]] = None,
    extra_resource_guarantees: Optional[Dict[str, str]] = None,
    tolerations: Optional[Union[List[str], List[V1Toleration]]] = None,
    env: Optional[Union[List[V1EnvVar], Mapping[str, str]]] = None,
) -> Tuple[V1Job, V1ConfigMap]:
    """
    Make a Kubernetes pod specification for a user-submitted job.
    """
    username = job.user.username
    name = "-".join([job.name, str(job.id)])
    image = job.image
    cmd = job.command
    script = job.script

    annotations = annotations or {}
    annotations.setdefault(
        "kbatch.jupyter.org/username",
        username,
    )

    labels = labels or {}
    labels = dict(labels)

    labels.setdefault(
        "kbatch.jupyter.org/username",
        escapism.escape(username, safe=SAFE_CHARS, escape_char="-"),
    )

    # TODO: alternative implementation for the script
    # What if instead of a ConfigMap, we have some kind of init container
    # that just pulls the script?
    # The workflow would be
    # 1. app puts the scrpit in blob storage
    # 2. init container pulls the script (maybe w/ a SAS token or some such)
    # This is maybe nicer since the user can refer back to the script they submitted.

    config_map = V1ConfigMap(
        data={"script": script},
        metadata=V1ObjectMeta(
            name=f"{name}-cm",
            namespace=namespace,
            labels=labels,
            annotations=annotations,
        ),
    )
    script_volume_mount = V1VolumeMount(mount_path="/code", name="script-volume")
    script_volume = V1Volume(
        name="script-volume",
        config_map=V1ConfigMapVolumeSource(
            name=f"{name}-cm", items=[V1KeyToPath(key="script", path="script")]
        ),
    )

    if isinstance(env, collections.abc.Mapping):
        env = [V1EnvVar(name=k, value=v) for k, v in env.items()]

    # TODO(TOM): figure out interaction between command /entrypoint and args.
    kwargs: Dict[str, Any]

    if script:
        kwargs = {
            "command": ["sh", "/code/script"],
        }
    else:
        kwargs = {"args": cmd}

    container = V1Container(
        **kwargs,
        image=image,
        name="job",
        env=env,
        volume_mounts=[script_volume_mount],
        resources=V1ResourceRequirements(),
    )

    container.resources.requests = {}

    if cpu_guarantee:
        container.resources.requests["cpu"] = cpu_guarantee
    if mem_guarantee:
        container.resources.requests["memory"] = mem_guarantee
    if extra_resource_guarantees:
        container.resources.requests.update(extra_resource_guarantees)

    container.resources.limits = {}
    if cpu_limit:
        container.resources.limits["cpu"] = cpu_limit
    if mem_limit:
        container.resources.limits["memory"] = mem_limit
    if extra_resource_limits:
        container.resources.limits.update(extra_resource_limits)

    pod_metadata = V1ObjectMeta(
        name=f"{name}-pod",
        namespace=namespace,
        labels=labels,
        annotations=annotations,
    )
    if tolerations:
        tolerations = [
            parse_toleration(v) if isinstance(v, str) else v for v in tolerations
        ]

    # TODO: verify restart policy
    template = V1PodTemplateSpec(
        spec=V1PodSpec(
            containers=[container],
            restart_policy="Never",
            volumes=[script_volume],
            tolerations=tolerations,
        ),
        metadata=pod_metadata,
    )

    job_metadata = V1ObjectMeta(
        name=name,
        annotations=annotations,
        labels=labels,
        namespace=namespace,
    )

    job = V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=job_metadata,
        spec=V1JobSpec(
            template=template, backoff_limit=4, ttl_seconds_after_finished=300
        ),
    )
    return job, config_map


@functools.lru_cache
def make_api() -> Tuple[client.CoreV1Api, client.BatchV1Api]:
    config.load_config()
    batch_api = client.BatchV1Api()
    api = client.CoreV1Api()
    return api, batch_api


def submit_configmap(api: client.CoreV1Api, config_map: V1ConfigMap):
    response = api.create_namespaced_config_map(namespace="default", body=config_map)
    return response


def submit_job(api: client.BatchV1Api, job: V1Job):
    # TODO: maybe make this an async generator of statuses.
    response = api.create_namespaced_job(namespace="default", body=job)
    return response


async def main():
    cmd = []
    token = str(uuid.uuid1())
    script = (pathlib.Path(__file__).parent.parent / "examples/script.sh").read_text()

    job, config_map = make_job(
        cmd,
        name=f"pi-{token}",
        image="mcr.microsoft.com/planetary-computer/python:2021.10.01.11",
        username="taugspurger@microsoft.com",
        script=script,
    )
    api, batch_api = make_api()
    print("submitting configmap")
    response = submit_configmap(api, config_map)
    print(response)

    print("submitting job")
    response = submit_job(batch_api, job)
    print(response)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
