import os
import functools
import logging
from typing import List, Optional, Tuple, Dict

from pydantic import BaseModel, BaseSettings
import jupyterhub.services.auth
from fastapi import Depends, FastAPI, HTTPException, Request, status, APIRouter
import kubernetes.client
import kubernetes.client.models
import kubernetes.config
import kubernetes.watch
import rich.traceback
from fastapi.responses import PlainTextResponse

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
    # lazy prefix handling. Will want to put nginx in front of this.
    kbatch_prefix: str = ""

    # Jobs are cleaned up by Kubernetes after this many seconds.
    kbatch_job_ttl_seconds_after_finished: Optional[int] = 3600
    # Additional environment variables to set in the job environment
    kbatch_job_extra_env: Optional[Dict[str, str]] = None

    # Whether to automatically create new namespaces for a users
    kbatch_create_user_namepsace: bool = True

    class Config:
        env_file = os.environ.get("KBATCH_SETTINGS_PATH", ".env")
        env_file_encoding = "utf-8"


settings = Settings()

app = FastAPI()
router = APIRouter(prefix=settings.kbatch_prefix)


class User(BaseModel):
    name: str
    groups: List[str]
    api_token: Optional[str]

    @property
    def namespace(self) -> str:
        """The Kubernetes namespace for a user."""
        return patch.namespace_for_username(self.name)


class UserOut(BaseModel):
    name: str
    groups: List[str]


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
        return User(**user, api_token=token, authenticated=True)
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


@router.get("/jobs/{job_name}")
async def read_job(job_name: str, user: User = Depends(get_current_user)):
    _, batch_api = get_k8s_api()
    result = batch_api.read_namespaced_job(job_name, user.namespace)
    return result.to_dict()


@router.get("/jobs/")
async def read_jobs(user: User = Depends(get_current_user)):
    _, batch_api = get_k8s_api()
    result = batch_api.list_namespaced_job(user.namespace)
    return result.to_dict()


@router.post("/jobs/")
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

    patch.patch(
        job,
        config_map,
        annotations={},
        labels={},
        username=user.name,
        ttl_seconds_after_finished=settings.kbatch_job_ttl_seconds_after_finished,
        extra_env=settings.kbatch_job_extra_env,
        api_token=user.api_token,
    )

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
        config_map = api.create_namespaced_config_map(
            namespace=user.namespace, body=config_map
        )
        patch.add_submitted_configmap_name(job, config_map)

    if settings.kbatch_create_user_namepsace:
        logger.info("Ensuring namespace %s", user.namespace)
        created = ensure_namespace(api, user.namespace)
        if created:
            logger.info("Created namespace %s", user.namespace)

    logger.info("Submitting job")
    resp = batch_api.create_namespaced_job(namespace=user.namespace, body=job)

    if config_map:
        logger.info(
            "patching configmap %s with owner %s",
            config_map.metadata.name,
            resp.metadata.name,
        )
        patch.patch_configmap_owner(resp, config_map)
        api.patch_namespaced_config_map(
            name=config_map.metadata.name, namespace=user.namespace, body=config_map
        )

    # TODO: set Job as the owner of the code.
    return resp.to_dict()


@router.get("/jobs/logs/{job_name}/", response_class=PlainTextResponse)
async def logs(job_name: str, user: User = Depends(get_current_user)):
    api, _ = get_k8s_api()
    logs = api.read_namespaced_pod_log(name=job_name, namespace=user.namespace)

    return logs

    # watch = kubernetes.watch.Watch()
    # for event in watch.stream(api.read_namespaced_pod_log, name=job_name,
    #                           namespace=user.namespace):
    #     # TODO: SSE
    #     print(event)


@router.get("/")
def get_root():
    return {"message": "kbatch"}


@router.get("/authorized")
def authorized(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(**user.dict())


app.include_router(router)


@app.get("/")
async def app_root():
    return {"message": "kbatch"}


# -------
# utils


def ensure_namespace(api: kubernetes.client.CoreV1Api, namespace: str):
    """
    Ensure that a Kubernetes namespace exists.

    Parameters
    ----------
    api : kubernetes
    """
    try:
        api.create_namespace(
            body=kubernetes.client.V1Namespace(
                metadata=kubernetes.client.V1ObjectMeta(name=namespace)
            )
        )
    except kubernetes.client.ApiException as e:
        if e.status == 409:
            # already exists
            return False
        # otherwise re-raise
        raise
    else:
        return True
