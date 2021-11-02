"""
Build and submit Jobs to Kubernetes.

This is used only by the kbatch backend. kbatch users do not have access to the Kubernetes API.
"""
import pathlib
import string
import shutil
import tempfile
import zipfile
from typing import Optional, List, Dict, Union

from kubernetes.client.models import (
    V1Job,
    V1JobSpec,
    V1PodSpec,
    V1PodTemplateSpec,
    V1ObjectMeta,
    # V1Toleration,
    V1ResourceRequirements,
    V1EnvVar,
    V1Container,
    V1ConfigMap,
)

from ._types import Job

SAFE_CHARS = set(string.ascii_lowercase + string.digits)


# def parse_toleration(t: str) -> V1Toleration:
#     if t.count("=") == 1 and t.count(":") == 1:
#         key, rest = t.split("=", 1)
#         value, effect = rest.split(":", 1)
#         return V1Toleration(key=key, value=value, effect=effect)
#     else:
#         raise ValueError(
#             f"Invalid toleration {t}. Should be of the form <key>=<value>:<effect>"
#         )


def make_job(
    job: Job,
) -> V1Job:
    """
    Make a Kubernetes pod specification for a user-submitted job.
    """
    name = job.name  # TODO: deduplicate somehow...
    image = job.image
    command = job.command
    args = job.args

    # annotations = k8s_config.annotations
    # labels = k8s_config.labels
    env = job.env

    # annotations = annotations or {}
    annotations: Dict[str, str] = {}
    # TODO: set in proxy

    # labels = labels or {}
    # labels = dict(labels)
    labels: Dict[str, str] = {}

    # file_volume_mount = V1VolumeMount(mount_path="/code", name="file-volume")
    # file_volume = V1Volume(name="file-volume", empty_dir={})

    env_vars: Optional[List[V1EnvVar]] = None
    if env:
        env_vars = [V1EnvVar(name=k, value=v) for k, v in env.items()]

    container = V1Container(
        args=args,
        command=command,
        image=image,
        name="job",
        env=env_vars,
        # volume_mounts=[file_volume_mount],
        resources=V1ResourceRequirements(),
        # TODO: this is important. validate it!
        working_dir="/code",
    )

    container.resources.requests = {}

    # if k8s_config.cpu_guarantee:
    #     container.resources.requests["cpu"] = k8s_config.cpu_guarantee
    # if k8s_config.mem_guarantee:
    #     container.resources.requests["memory"] = k8s_config.mem_guarantee
    # if k8s_config.extra_resource_guarantees:
    #     container.resources.requests.update(k8s_config.extra_resource_guarantees)

    # container.resources.limits = {}
    # if k8s_config.cpu_limit:
    #     container.resources.limits["cpu"] = k8s_config.cpu_limit
    # if k8s_config.mem_limit:
    #     container.resources.limits["memory"] = k8s_config.mem_limit
    # if k8s_config.extra_resource_limits:
    #     container.resources.limits.update(k8s_config.extra_resource_limits)

    pod_metadata = V1ObjectMeta(
        name=f"{name}-pod",
        # namespace=k8s_config.namespace,
        labels=labels,
        annotations=annotations,
    )
    tolerations = None
    # if k8s_config.tolerations:
    #     tolerations: Optional[List[Any]] = [
    #         parse_toleration(v) if isinstance(v, str) else v
    #         for v in k8s_config.tolerations
    #     ]
    # else:
    #     tolerations = None

    # TODO: verify restart policy
    template = V1PodTemplateSpec(
        spec=V1PodSpec(
            # init_containers=init_containers,
            containers=[container],
            restart_policy="Never",
            # volumes=[file_volume],
            tolerations=tolerations,
        ),
        metadata=pod_metadata,
    )

    generate_name = name
    if not name.endswith("-"):
        generate_name = name + "-"

    job_metadata = V1ObjectMeta(
        generate_name=generate_name,
        annotations=annotations,
        labels=labels,
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


def make_configmap(code: Union[str, pathlib.Path], generate_name) -> V1ConfigMap:
    code = pathlib.Path(code)

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "code"
        zp = p.with_suffix(".zip")

        if code.is_dir():
            shutil.make_archive(str(p), "zip", str(code))
        else:
            with zipfile.ZipFile(zp, mode="w") as zf:
                zf.write(str(code))

        data = zp.read_bytes()

    metadata = V1ObjectMeta(generate_name=generate_name)
    cm = V1ConfigMap(
        api_version="v1",
        binary_data={"code": data},
        kind="ConfigMap",
        metadata=metadata,
    )
    return cm
