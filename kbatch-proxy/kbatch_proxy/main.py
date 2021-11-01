import os
import functools
import logging
from typing import List, Optional

from pydantic import BaseModel, BaseSettings
import jupyterhub.services.auth
from fastapi import Depends, FastAPI, HTTPException, Request, status
import kubernetes.client
import kubernetes.config
import kubernetes.client.models
import rich.traceback

rich.traceback.install()

from . import patch
from . import utils

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # kbatch_job_namespace: str = "default"
    # kbatch_job_cpu_guarantee: Optional[str] = None
    # kbatch_job_cpu_limit: Optional[str] = None
    # kbatch_job_mem_guarantee: Optional[str] = None
    # kbatch_job_mem_limit: Optional[str] = None
    # kbatch_job_tolerations: Optional[List[str]]

    jupyterhub_api_token: str = "super-secret"
    jupyterhub_service_prefix: str = "/"

    class Config:
        env_file = os.environ.get("KBATCH_SETTINGS_PATH", ".env")
        env_file_encoding = "utf-8"


settings = Settings()

app = FastAPI()


class User(BaseModel):
    authenticated: bool
    name: Optional[str]
    groups: Optional[List[str]]

    @property
    def namespace(self):
        """The Kubernetes namespace for a user."""
        return patch.namespace_for_username(self.name)


# ----------------------------------------------------------------------------
# Jupyterhub configuration
# TODO: make auth pluggable

auth = jupyterhub.services.auth.HubAuth(
    api_token=settings.jupyterhub_api_token,
    cache_max_age=60,
)


async def get_current_user(request: Request) -> User:
    cookie = request.cookies.get(auth.cookie_name)
    token = request.headers.get(auth.auth_header_name)

    if cookie:
        user = auth.user_for_cookie(cookie)
    elif token:
        token = token.removeprefix("token ").removeprefix("Token ")
        user = auth.user_for_token(token)
    else:
        user = None

    if user:
        return User(**user, authenticated=True)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect token",
        )


# ----------------------------------------------------------------------------
# Kubernetes backend configuration


@functools.lru_cache
def get_k8s_api() -> kubernetes.client.BatchV1Api:
    kubernetes.config.load_config()

    batch_api = kubernetes.client.BatchV1Api()
    return batch_api


# ----------------------------------------------------------------------------
# app


@app.get("/jobs/{job_name}")
async def read_job(job_name: str, user: User = Depends(get_current_user)):
    api = get_k8s_api()
    result = api.read_namespaced_job(job_name, user.namespace)
    return result.to_dict()


@app.get("/jobs/")
async def read_jobs(user: User = Depends(get_current_user)):
    api = get_k8s_api()
    result = api.list_namespaced_job(user.namespace)
    return result.to_dict()


@app.post("/jobs/")
async def create_job(request: Request, user: User = Depends(get_current_user)):
    batch_api = get_k8s_api()

    data = await request.json()
    d = data["job"]
    job: kubernetes.client.models.V1Job = utils.parse(
        d, model=kubernetes.client.models.V1Job
    )

    patch.patch_job(job, annotations={}, labels={}, username=user.name)

    logger.info("Submitting job")
    resp = batch_api.create_namespaced_job(namespace=user.namespace, body=job)

    return resp.to_dict()


@app.get("/")
async def app_root():
    return {"message": "kbatch"}
