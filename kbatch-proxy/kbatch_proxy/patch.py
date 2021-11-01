"""
Patch a V1Job.
"""
import string

import escapism
from kubernetes.client.models import V1Job


SAFE_CHARS = set(string.ascii_lowercase + string.digits)


def add_annotations(job: V1Job, annotations, username: str) -> None:
    # TODO: set in proxy
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


def add_namespace(job: V1Job, namespace) -> None:
    job.metadata.namespace = namespace
    job.spec.template.metadata.namespace = namespace


def namespace_for_username(username: str) -> str:
    return username


def patch_job(job: V1Job, *, annotations, labels, username: str) -> None:
    add_annotations(job, annotations, username)
    add_labels(job, labels, username)
    add_namespace(job, namespace_for_username(username))
