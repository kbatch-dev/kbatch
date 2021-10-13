"""
Build and submit Jobs to Kubernetes.

This is used only by the kbatch backend. kbatch users do not have access to the Kubernetes API.
"""
import asyncio
import uuid
from typing import List

from kubernetes import client
from kubernetes import config
from kubernetes.client.models import (
    V1Job,
    V1JobSpec,
    V1PodSpec,
    V1PodTemplateSpec,
    V1ObjectMeta,
)
from kubernetes.client.models.v1_container import V1Container


# TODO: figure out how to associate with a user. Attach it as a label  or annotation probably.
# TODO: figure out how to "upload" files.
# TODO: get job logs, cache to storage, delete pods
# TODO: clean up jobs


def make_job(
    cmd: List[str],
    name: str,
    image: str,
    username: ...,  # either the name or ID...
) -> V1Job:
    """
    Make a Kubernetes pod specification for a user-submitted job.
    """
    container = V1Container(args=cmd, image=image, name="job")
    # TODO: verify restarty policy
    template = V1PodTemplateSpec(
        spec=V1PodSpec(containers=[container], restart_policy="Never")
    )
    job_metadata = V1ObjectMeta(name=name)
    job = V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=job_metadata,
        spec=V1JobSpec(template=template, backoff_limit=4),
    )
    return job


def make_api():
    config.load_config()
    api = client.BatchV1Api()
    return api


async def submit_job(api, job):
    # TODO: maybe make this an async generator of statuses.
    # await submit_job(api, job)
    print("submitting job")
    response = api.create_namespaced_job(namespace="default", body=job)
    return response


async def main():
    cmd = ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
    token = str(uuid.uuid1())
    job = make_job(
        cmd, name=f"pi-{token}", image="perl", user="taugspurger@microsoft.com"
    )
    api = make_api()
    response = await submit_job(api, job)
    print(response)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
