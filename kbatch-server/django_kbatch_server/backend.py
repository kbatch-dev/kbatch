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
from typing import Dict, Optional, List, Union, Mapping

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
    cpu_guarantee: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    mem_limit: Optional[str] = None,
    mem_guarantee: Optional[str] = None,
    extra_resource_limits: Optional[Dict[str, str]] = None,
    extra_resource_guarantees: Optional[Dict[str, str]] = None,
    tolerations: Optional[Union[List[str], List[V1Toleration]]] = None,
    env: Optional[Union[List[V1EnvVar], Mapping[str, str]]] = None,
) -> V1Job:
    """
    Make a Kubernetes pod specification for a user-submitted job.
    """
    username = job.user.username
    name = "-".join([job.name, str(job.id)])
    image = job.image
    command = job.command
    args = job.args

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

    file_volume_mount = V1VolumeMount(mount_path="/code", name="file-volume")
    file_volume = V1Volume(name="file-volume", empty_dir={})

    if isinstance(env, collections.abc.Mapping):
        env = [V1EnvVar(name=k, value=v) for k, v in env.items()]

    if args is None and command and job.upload:
        args = [f"/code/{job.upload.file.name}"]

    container = V1Container(
        args=args,
        command=command,
        image=image,
        name="job",
        env=env,
        volume_mounts=[file_volume_mount],
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

    init_containers = None
    if job.upload:
        init_containers = [
            V1Container(
                args=[
                    "wget",
                    job.upload.file.url,
                    "-O",
                    f"/code/{job.upload.file.name}",
                ],
                image="inutano/wget:1.20.3-r1",
                name=f"{name}-init",
                volume_mounts=[file_volume_mount],
            )
        ]

    # TODO: verify restart policy
    template = V1PodTemplateSpec(
        spec=V1PodSpec(
            init_containers=init_containers,
            containers=[container],
            restart_policy="Never",
            volumes=[file_volume],
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
    return job


@functools.lru_cache
def make_api() -> client.BatchV1Api:
    config.load_config()
    batch_api = client.BatchV1Api()
    return batch_api


def submit_job(api: client.BatchV1Api, job: V1Job):
    # TODO: maybe make this an async generator of statuses.
    response = api.create_namespaced_job(namespace="default", body=job)
    return response


async def main():
    cmd = []
    token = str(uuid.uuid1())
    script = (pathlib.Path(__file__).parent.parent / "examples/script.sh").read_text()

    job = make_job(
        cmd,
        name=f"pi-{token}",
        image="mcr.microsoft.com/planetary-computer/python:2021.10.01.11",
        username="taugspurger@microsoft.com",
        script=script,
    )
    batch_api = make_api()

    print("submitting job")
    response = submit_job(batch_api, job)
    print(response)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
