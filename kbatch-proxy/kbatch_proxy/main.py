import os
import functools
import logging
from typing import List, Optional, Tuple

from pydantic import BaseModel, BaseSettings
import jupyterhub.services.auth
from fastapi import Depends, FastAPI, HTTPException, Request, status
import kubernetes.client
import kubernetes.config
import kubernetes.client.models
import rich.traceback

from . import patch
from . import utils

rich.traceback.install()

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
    name: str
    groups: List[str]

    @property
    def namespace(self) -> str:
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
def get_k8s_api() -> Tuple[kubernetes.client.CoreV1Api, kubernetes.client.BatchV1Api]:
    kubernetes.config.load_config()

    return kubernetes.client.CoreV1Api(), kubernetes.client.BatchV1Api()


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
    api, batch_api = get_k8s_api()

    data = await request.json()
    job_data = data["job"]
    job: kubernetes.client.models.V1Job = utils.parse(
        job_data, model=kubernetes.client.models.V1Job
    )

    code_data = data.get("code", None)
    if code_data:
        # The contents were base64encoded prior to being JSON serialized
        # we have to decode it *after* submitting things to the API server...
        # This is not great.
        # code_data["binary_data"]["code"] = base64.b64decode(code_data["binary_data"]["code"])
        config_map: Optional[kubernetes.client.models.V1ConfigMap] = utils.parse(
            code_data, model=kubernetes.client.models.V1ConfigMap
        )
    else:
        config_map = None

    patch.patch(job, config_map, annotations={}, labels={}, username=user.name)

    # What needs to happen when? We have a few requirements
    # 1. The code ConfigMap must exist before adding it as a volume (we need a name,
    #    and k8s requires that)
    # 2. MAYBE: The Job must exist before adding it as an owner for the ConfigMap
    #
    # So I think we're at 3 requests:
    #
    # 1. Submit configmap
    #   - ..
    # 2. Submit Job
    # 3. Patch ConfigMap to add Job as the owner

    if config_map:
        logger.info("Submitting ConfigMap")
        resp = api.create_namespaced_config_map(
            namespace=user.namespace, body=config_map
        )
        patch.add_submitted_configmap_name(job, resp)

    logger.info("Submitting job")
    resp = batch_api.create_namespaced_job(namespace=user.namespace, body=job)

    # TODO: set Job as the owner of the code.
    return resp.to_dict()


@app.get("/")
async def app_root():
    return {"message": "kbatch"}
