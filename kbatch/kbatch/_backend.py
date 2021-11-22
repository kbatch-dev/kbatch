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
    V1Toleration,
    V1ResourceRequirements,
    V1EnvVar,
    V1Container,
    V1ConfigMap,
    V1Affinity,
    V1NodeAffinity,
    V1NodeSelector,
    V1NodeSelectorTerm,
    V1NodeSelectorRequirement,
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
    profile: Optional[dict] = None,
) -> V1Job:
    """
    Make a Kubernetes pod specification for a user-submitted job.
    """
    profile = profile or {}
    name = job.name  # TODO: deduplicate somehow...
    image = job.image or profile.get("image", None)
    if image is None:
        raise TypeError(
            "Must specify 'image', either with `--image` or from the profile."
        )

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

    resources = profile.get("resources", {})
    limits = resources.get("limits", {})
    requests = resources.get("requests", {})

    container.resources.requests = {}
    container.resources.limits = {}

    if requests:
        container.resources.requests.update(requests)
    if limits:
        container.resources.limits.update(limits)

    pod_metadata = V1ObjectMeta(
        name=f"{name}-pod",
        # namespace=k8s_config.namespace,
        labels=labels,
        annotations=annotations,
    )
    tolerations = None
    if profile.get("tolerations", []):
        tolerations = [V1Toleration(**v) for v in profile["tolerations"]]

    node_affinity_required = profile.get("node_affinity_required", {})
    if node_affinity_required:
        match_expressions = []
        match_fields = []
        for d in node_affinity_required:
            for k, affinities in d.items():
                for v in affinities:
                    if k == "matchExpressions":
                        match_expressions.append(
                            V1NodeSelectorRequirement(
                                key=v.get("key"),
                                operator=v.get("operator"),
                                values=v.get("values"),
                            )
                        )
                    elif k == "matchFields":
                        match_fields.append(
                            V1NodeSelectorRequirement(
                                key=v.get("key"),
                                operator=v.get("operator"),
                                values=v.get("values"),
                            )
                        )
                    else:
                        raise ValueError(
                            "Key must be 'matchExpressions' or 'matchFields'. Got {k} instead."
                        )

        node_selector_terms = V1NodeSelectorTerm(
            match_expressions=match_expressions,
            match_fields=match_fields,
        )
        node_selector = V1NodeSelector(node_selector_terms=[node_selector_terms])
        node_affinity = V1NodeAffinity(
            required_during_scheduling_ignored_during_execution=node_selector
        )
        affinity = V1Affinity(node_affinity=node_affinity)
    else:
        affinity = None

    # TODO: verify restart policy
    template = V1PodTemplateSpec(
        spec=V1PodSpec(
            # init_containers=init_containers,
            containers=[container],
            restart_policy="Never",
            # volumes=[file_volume],
            tolerations=tolerations,
            affinity=affinity,
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
            template=template, backoff_limit=0, ttl_seconds_after_finished=300
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
