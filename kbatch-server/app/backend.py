"""
Build and submit Jobs to Kubernetes.

This is used only by the kbatch backend. kbatch users do not have access to the Kubernetes API.
"""
import asyncio
import functools
import pathlib
import string
import escapism
import uuid
from typing import Dict, Tuple

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
)
from kubernetes.client.models.v1_container import V1Container

from .models import Job

# TODO: figure out how to associate with a user. Attach it as a label  or annotation probably.
# TODO: figure out how to "upload" files.
# TODO: get job logs, cache to storage, delete pods
# TODO: clean up jobs
# TODO: Insert env vars for Dask Gateawy (JUPYTERHUB_API_TOKEN, auth, image, proxy, etc.)

SAFE_CHARS = set(string.ascii_lowercase + string.digits)


def make_job(
    job: Job,
    namespace: str = "default",
    labels: str = None,
    annotations: Dict[str, str] = None,
    script: str = None,
) -> V1Job:
    """
    Make a Kubernetes pod specification for a user-submitted job.
    """
    username = job.username
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
    labels.setdefault(
        "kbatch.jupyter.org/username",
        escapism.escape(username, safe=SAFE_CHARS, escape_char="-"),
    )

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

    if script:
        kwargs = {
            "command": ["sh", "/code/script"],
        }
    else:
        kwargs = {"args": cmd}

    container = V1Container(
        **kwargs, image=image, name="job", volume_mounts=[script_volume_mount]
    )

    pod_metadata = V1ObjectMeta(
        name=f"{name}-pod",
        namespace=namespace,
        labels=labels,
        annotations=annotations,
    )

    # TODO: verify restart policy
    template = V1PodTemplateSpec(
        spec=V1PodSpec(
            containers=[container], restart_policy="Never", volumes=[script_volume]
        ),
        metadata=pod_metadata,
    )

    job_metadata = V1ObjectMeta(
        name=name,
        annotations=annotations,
        labels=labels,
        namespace=namespace,
    )
    # TODO: use ttlSecondsAfterFinished for cleanup
    # https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs
    # requires k8s v1.21 [beta]
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


async def submit_configmap(api: client.CoreV1Api, config_map: V1ConfigMap):
    response = api.create_namespaced_config_map(namespace="default", body=config_map)
    return response


async def submit_job(api: client.BatchV1Api, job: V1Job):
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
    response = await submit_configmap(api, config_map)
    print(response)

    print("submitting job")
    response = await submit_job(batch_api, job)
    print(response)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
