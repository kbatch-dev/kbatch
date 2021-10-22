from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Dict, Optional, Mapping

from django.conf import settings
from django.core.files import File

if TYPE_CHECKING:
    from . import models


@dataclass(frozen=True)
class User:
    username: str


@dataclass(frozen=True)
class Upload:
    file: File

    @classmethod
    def from_model(cls, upload):
        return cls(file=upload.file)


@dataclass(frozen=True)
class Job:
    user: User
    name: str
    id: int
    image: str
    command: Optional[List[str]]
    args: Optional[List[str]] = None
    env: Optional[List[Dict[str, str]]] = None
    upload: Optional[Upload] = None

    @classmethod
    def from_model(cls, job: "models.Job"):
        return cls(
            user=User(username=job.user.username),
            name=job.name,
            id=job.id,
            image=job.image,
            command=job.command,
            args=job.args,
            env=job.env,
            upload=Upload.from_model(job.upload) if job.upload else None,
        )


@dataclass(frozen=True)
class KubernetesConfig:
    namespace: str = "default"
    labels: Optional[Mapping[str, str]] = None
    annotations: Optional[Dict[str, str]] = None
    cpu_limit: Optional[str] = None
    cpu_guarantee: Optional[str] = None
    mem_limit: Optional[str] = None
    mem_guarantee: Optional[str] = None
    tolerations: Optional[List[str]] = None
    extra_resource_limits: Optional[Dict[str, str]] = None
    extra_resource_guarantees: Optional[Dict[str, str]] = None

    @classmethod
    def from_settings(cls):
        return cls(
            namespace=settings.KBATCH_JOB_NAMESPACE,
            cpu_guarantee=settings.KBATCH_JOB_CPU_GUARANTEE,
            cpu_limit=settings.KBATCH_JOB_CPU_LIMIT,
            mem_guarantee=settings.KBATCH_JOB_MEM_GUARANTEE,
            mem_limit=settings.KBATCH_JOB_MEM_LIMIT,
            tolerations=settings.KBATCH_JOB_TOLERATIONS,
            labels=settings.KBATCH_JOB_LABELS,
            annotations=settings.KBATCH_JOB_ANNOTATIONS,
            extra_resource_limits=settings.KBATCH_JOB_EXTRA_RESOURCE_LIMITS,
            extra_resource_guarantees=settings.KBATCH_JOB_EXTRA_RESOURCE_GUARANTEES,
        )
