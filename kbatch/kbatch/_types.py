# TODO: this can all probably be deleted.
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Mapping


@dataclass(frozen=True)
class User:
    username: str


@dataclass()
class Job:
    name: str
    image: str
    command: Optional[List[str]]
    args: Optional[List[str]] = None
    upload: Optional[str] = None
    description: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    code: Optional[str] = None

    def inject_default_env(self, default_env: Dict[str, str]) -> None:
        """
        Inserts the default environment into self.env, with precedence given to self.env.

        Mutates `self` inplace.
        """
        self.env = {**default_env, **(self.env or {})}

    def to_kubernetes(self):
        from ._backend import make_job

        return make_job(self)


@dataclass(frozen=True)
class KubernetesConfig:
    labels: Optional[Mapping[str, str]] = None
    annotations: Optional[Dict[str, str]] = None
    cpu_limit: Optional[str] = None
    cpu_guarantee: Optional[str] = None
    mem_limit: Optional[str] = None
    mem_guarantee: Optional[str] = None
    tolerations: Optional[List[str]] = None
    extra_resource_limits: Optional[Dict[str, str]] = None
    extra_resource_guarantees: Optional[Dict[str, str]] = None
