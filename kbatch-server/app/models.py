from typing import Optional, List, Dict
from pydantic import BaseModel


class JobIn(BaseModel):
    command: Optional[List[str]]
    script: Optional[str]
    image: str
    name: Optional[str]
    env: Optional[Dict[str, str]]


class Job(BaseModel):
    id: int
    name: str
    command: Optional[List[str]]
    script: Optional[str]
    image: str
    username: str
    # TODO: figure out if we should return env here
    env: Optional[Dict[str, str]]


class User(BaseModel):
    authenticated: bool
    redirect_url: Optional[str]
    name: Optional[str]
    groups: Optional[List[str]]
