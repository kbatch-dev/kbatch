"""
Patch a V1Job.
"""
import re
import string
from typing import Optional

import escapism
from kubernetes.client.models import (
    V1Job,
    V1ConfigMap,
    V1Container,
    V1VolumeMount,
    V1Volume,
    V1ConfigMapVolumeSource,
    V1KeyToPath,
)


SAFE_CHARS = set(string.ascii_lowercase + string.digits)


def add_annotations(job: V1Job, annotations, username: str) -> None:
    annotations = dict(annotations)
    annotations["kbatch.jupyter.org/username"] = username

    job.metadata.annotations.update(annotations)  # update or replace?
    job.spec.template.metadata.annotations.update(annotations)  # update or replace?


def add_labels(job: V1Job, labels, username: str) -> None:
    labels = dict(labels)
    labels["kbatch.jupyter.org/username"] = escapism.escape(
        username, safe=SAFE_CHARS, escape_char="-"
    )

    job.metadata.labels.update(labels)  # update or replace?
    job.spec.template.metadata.labels.update(labels)  # update or replace?


def add_namespace(job: V1Job, namespace: str) -> None:
    job.metadata.namespace = namespace
    job.spec.template.metadata.namespace = namespace


def add_namespace_configmap(config_map: V1ConfigMap, namespace: str) -> None:
    config_map.metadata.namespace = namespace


def add_code_configmap(job: V1Job) -> None:
    pass


def add_unzip_init_container(job: V1Job) -> None:
    """
    Adds an init container to unzip the code.
    """
    # containers = job.spec.template.spec.containers
    code_volume = V1Volume(
        name="code-source-volume",
        config_map=V1ConfigMapVolumeSource(
            name="code-source-volume",
            optional=False,
            items=[V1KeyToPath(key="code", path="code.b64")],
        ),
    )
    code_dst_volume = V1Volume(name="code-volume", empty_dir={})
    code_dst_volume_mount = V1VolumeMount(mount_path="/code", name="code-volume")

    code_volume_mount = V1VolumeMount(
        mount_path="/code-zipped", name="code-source-volume", read_only=False
    )

    unzip_container = V1Container(
        args=[
            "-c",
            (
                # apparently Kubernetes takes care of base64decoding?
                # "base64 -d /code-zipped/code.b64 > /code.zip; "
                "echo [unzip]; "
                "unzip -d /code/ /code-zipped/code.b64 ;"
                "echo [ls code] ; "
                "ls /code ;"
            ),
        ],
        command=["/bin/sh"],
        image="busybox",
        name=job.metadata.generate_name + "-init",
        volume_mounts=[code_volume_mount, code_dst_volume_mount],
    )
    if job.spec.template.spec.init_containers is None:
        job.spec.template.spec.init_containers = [unzip_container]
    else:
        job.spec.template.spec.init_containers.insert(0, unzip_container)

    # patch_job_with_submitted_configmap relies on the ordering here.
    volumes = [code_volume, code_dst_volume]

    if job.spec.template.spec.volumes is None:
        job.spec.template.spec.volumes = volumes
    else:
        job.spec.template.spec.volumes.extend(volumes)

    if job.spec.template.spec.containers[0].volume_mounts is None:
        job.spec.template.spec.containers[0].volume_mounts = [code_dst_volume_mount]
    else:
        job.spec.template.spec.containers[0].volume_mounts.append(code_dst_volume_mount)


def namespace_for_username(username: str) -> str:
    """
    Get the Kubernetes namespace for a JupyterHub user.

    Not all JupyterHub usernames are validate kubernetes namespaces, so we have to
    # translate it somehow. This replaces lowercases the input and replaces
    non-ascii alphanumeric characters with "-".
    """
    return re.sub(r"[^a-z0-9]", "-", username.lower())


def patch(
    job: V1Job, config_map: Optional[V1ConfigMap], *, annotations, labels, username: str
) -> None:
    """
    Updates the Job inplace with the following modifications:

    * Adds `annotations` to the job
    * Adds `labels` to the job
    * Sets the namespace of the job (and all containers) and ConfigMap to `namespacee`
    * Adds the ConfigMap as a volume for the Job's container
    """
    add_annotations(job, annotations, username)
    add_labels(job, labels, username)
    add_namespace(job, namespace_for_username(username))
    if config_map:
        add_namespace_configmap(config_map, namespace_for_username(username))
        add_unzip_init_container(job)


def add_submitted_configmap_name(job: V1Job, config_map: V1ConfigMap):
    # config_map should be the response from the Kubernetes API server with the
    # submitted name
    job.spec.template.spec.volumes[-2].config_map.name = config_map.metadata.name
