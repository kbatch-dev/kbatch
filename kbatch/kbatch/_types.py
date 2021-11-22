# TODO: this can all probably be deleted.
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass(frozen=True)
class User:
    username: str


@dataclass()
class Job:
    name: str
    image: Optional[str] = None
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    upload: Optional[str] = None
    description: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    code: Optional[str] = None

    def to_kubernetes(self):
        from ._backend import make_job

        return make_job(self)
