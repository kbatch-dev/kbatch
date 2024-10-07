"""
Patch a V1Job.
"""

import base64
import hashlib
import re
import string
from typing import Dict, Optional, Union

import escapism
from kubernetes.client.models import (
    V1ConfigMap,
    V1ConfigMapVolumeSource,
    V1Container,
    V1CronJob,
    V1EnvVar,
    V1EnvVarSource,
    V1Job,
    V1JobTemplateSpec,
    V1KeyToPath,
    V1ObjectMeta,
    V1OwnerReference,
    V1Secret,
    V1SecretKeySelector,
    V1Volume,
    V1VolumeMount,
)

SAFE_CHARS = set(string.ascii_lowercase + string.digits)


def add_annotations(
    job: Union[V1Job, V1JobTemplateSpec], annotations, username: str
) -> None:
    annotations = dict(annotations)
    annotations["kbatch.jupyter.org/username"] = username

    job.metadata.annotations.update(annotations)  # update or replace?
    job.spec.template.metadata.annotations.update(annotations)  # update or replace?


def add_labels(job: Union[V1Job, V1JobTemplateSpec], labels, username: str) -> None:
    labels = dict(labels)
    labels["kbatch.jupyter.org/username"] = escapism.escape(
        username, safe=SAFE_CHARS, escape_char="-"
    )

    job.metadata.labels.update(labels)  # update or replace?
    job.spec.template.metadata.labels.update(labels)  # update or replace?


def add_namespace(job: Union[V1Job, V1JobTemplateSpec], namespace: str) -> None:
    job.metadata.namespace = namespace
    job.spec.template.metadata.namespace = namespace


def add_namespace_configmap(config_map: V1ConfigMap, namespace: str) -> None:
    config_map.metadata.namespace = namespace


def add_code_configmap(job: Union[V1Job, V1JobTemplateSpec]) -> None:
    pass


def add_unzip_init_container(job: Union[V1Job, V1JobTemplateSpec]) -> None:
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


def add_extra_env(
    job: Union[V1Job, V1JobTemplateSpec],
    extra_env: Dict[str, str],
    api_token: Optional[str] = None,
) -> None:
    container = job.spec.template.spec.containers[0]
    env_vars = [V1EnvVar(name=name, value=value) for name, value in extra_env.items()]

    image = job.spec.template.spec.containers[0].image

    env_vars.extend(
        [
            V1EnvVar(name="JUPYTER_IMAGE", value=image),
            V1EnvVar(name="JUPYTER_IMAGE_SPEC", value=image),
        ]
    )

    if api_token:
        # TODO: use a k8s secret
        env_vars.append(V1EnvVar(name="JUPYTERHUB_API_TOKEN", value=api_token))

    if container.env is None:
        container.env = env_vars
    else:
        container.env.extend(env_vars)


def namespace_for_username(username: str) -> str:
    """
    Get the Kubernetes namespace for a JupyterHub user.

    Not all JupyterHub usernames are valid kubernetes namespaces, so we have to
    translate it somehow. To make namespaces safe and valid, this:

    - adds `kbatch-` prefix
    - replaces all non-alphanumeric characters with `-`
    - truncates to 32 characters
    - strips trailing '-'

    If the name was transformed by this process, append hash to avoid collisions.
    """
    # trim to safe characters and length
    safe_username = re.sub(r"[^a-z0-9]+", "-", username.lower())[:40].strip("-")
    if safe_username != username:
        # transform did something, append hash to avoid collisions
        hash = hashlib.sha256(username.encode("utf8")).hexdigest()[:7]
        safe_username = f"{safe_username}--{hash}"
    return f"kbatch-{safe_username}"


def add_job_ttl_seconds_after_finished(
    job: Union[V1Job, V1JobTemplateSpec], ttl_seconds_after_finished: Optional[int]
) -> None:
    job.spec.ttl_seconds_after_finished = ttl_seconds_after_finished


def extract_env_secret(job: Union[V1Job, V1JobTemplateSpec]):
    """Extract all V1EnvVars into a Secret"""
    meta = V1ObjectMeta(
        name=job.metadata.name,
        generate_name=job.metadata.generate_name,
        labels=job.metadata.labels,
    )
    secret = V1Secret(metadata=meta, type="Opaque", data={})
    for container in job.spec.template.spec.containers:
        for i, env in enumerate(container.env or []):
            if env.value is not None:
                secret.data[env.name] = base64.b64encode(
                    env.value.encode("utf8")
                ).decode("ascii")
                container.env[i] = V1EnvVar(
                    name=env.name,
                    value_from=V1EnvVarSource(
                        secret_key_ref=V1SecretKeySelector(
                            key=env.name,
                            name=secret.metadata.generate_name,
                        )
                    ),
                )
    return secret


def add_env_secret_name(job: Union[V1Job, V1JobTemplateSpec], secret: V1Secret):
    """Apply the secret name to env secrets once they are known"""
    generate_name = secret.metadata.generate_name
    name = secret.metadata.name
    for container in job.spec.template.spec.containers:
        for i, env in enumerate(container.env or []):
            if (
                env.value_from
                and env.value_from.secret_key_ref
                and env.value_from.secret_key_ref.name == generate_name
            ):
                env.value_from.secret_key_ref.name = name


def patch(
    job: Union[V1Job, V1JobTemplateSpec],
    config_map: Optional[V1ConfigMap] = None,
    *,
    username: str,
    annotations: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None,
    extra_env: Optional[Dict[str, str]] = None,
    api_token: Optional[str] = None,
    ttl_seconds_after_finished: Optional[int] = 3600,
) -> None:
    """
    Updates the Job inplace with the following modifications:

    * Adds `annotations` to the job
    * Adds `labels` to the job
    * Sets the namespace of the job (and all containers) and ConfigMap to `namespace`
    * Adds the ConfigMap as a volume for the Job's container
    """
    annotations = annotations or {}
    labels = labels or {}
    extra_env = extra_env or {}

    add_annotations(job, annotations, username)
    add_labels(job, labels, username)
    add_namespace(job, namespace_for_username(username))
    add_extra_env(job, extra_env, api_token)
    add_job_ttl_seconds_after_finished(job, ttl_seconds_after_finished)

    if config_map:
        add_namespace_configmap(config_map, namespace_for_username(username))
        add_unzip_init_container(job)


def add_submitted_configmap_name(
    job: Union[V1Job, V1JobTemplateSpec], config_map: V1ConfigMap
):
    # config_map should be the response from the Kubernetes API server with the
    # submitted name
    job.spec.template.spec.volumes[-2].config_map.name = config_map.metadata.name


def patch_owner(job: Union[V1Job, V1CronJob], obj: V1ConfigMap | V1Secret):
    if job.metadata.name is None:
        raise ValueError("job must have a name before it can be set as an owner")
    assert job.metadata.name is not None

    obj.metadata.owner_references = [
        V1OwnerReference(
            api_version="batch/v1",
            kind=job.kind,
            name=job.metadata.name,
            uid=job.metadata.uid,
        )
    ]
