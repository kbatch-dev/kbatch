from typing import Optional, List
from pydantic import BaseModel


class JobIn(BaseModel):
    command: Optional[List[str]]
    script: Optional[str]
    image: str
    name: Optional[str]


class Job(BaseModel):
    id: int
    name: str
    command: Optional[List[str]]
    script: Optional[str]
    image: str
    username: str


class User(BaseModel):
    authenticated: bool
    redirect_url: Optional[str]
    name: Optional[str]
    groups: Optional[List[str]]
