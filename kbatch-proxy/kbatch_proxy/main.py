import os
import logging
from typing import List, Optional, Tuple, Dict, Union

import yaml
from pydantic import BaseModel, BaseSettings
import jupyterhub.services.auth
from fastapi import Depends, FastAPI, HTTPException, Request, status, APIRouter
import kubernetes.client
from kubernetes.client.models import V1CronJob, V1Job, V1ConfigMap
import kubernetes.config
import kubernetes.watch
import rich.traceback
from fastapi.responses import StreamingResponse, Response

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
    kbatch_init_logging: bool = True
    # lazy prefix handling. Will want to put nginx in front of this.
    kbatch_prefix: str = ""

    # A path to a YAML file defining a job template
    kbatch_job_template_file: Optional[str] = None

    # A path to a YAML file defining the profiles
    kbatch_profile_file: Optional[str] = None

    # Jobs are cleaned up by Kubernetes after this many seconds.
    kbatch_job_ttl_seconds_after_finished: Optional[int] = 3600
    # Additional environment variables to set in the job environment
    kbatch_job_extra_env: Optional[Dict[str, str]] = None

    # Whether to automatically create new namespaces for a users
    kbatch_create_user_namespace: bool = True

    class Config:
        env_file = os.environ.get("KBATCH_SETTINGS_PATH", ".env")
        env_file_encoding = "utf-8"


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


settings = Settings()
if settings.kbatch_init_logging:
    import rich.logging

    handler = rich.logging.RichHandler()
    logger.setLevel(logging.INFO)
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(lineno)s:%(message)s")
    )
    logger.addHandler(handler)

if settings.kbatch_job_template_file:
    logger.info("loading job template from %s", settings.kbatch_job_template_file)
    with open(settings.kbatch_job_template_file) as f:
        job_template = yaml.safe_load(f)

    # parse with Kubernetes to normalize keys with job_data
    job_template = utils.parse(job_template, model=V1Job).to_dict()
    utils.remove_nulls(job_template)

else:
    job_template = None


if settings.kbatch_profile_file:
    # TODO: we need some kind of validation on the keys / values here. Catch typos...
    logger.info("loading profiles from %s", settings.kbatch_profile_file)
    with open(settings.kbatch_profile_file) as f:
        profile_data = yaml.safe_load(f)
else:
    profile_data = {}


app = FastAPI()
router = APIRouter(prefix=settings.kbatch_prefix)


# ----------------------------------------------------------------------------
# Jupyterhub configuration
# TODO: make auth pluggable

auth = jupyterhub.services.auth.HubAuth(
    api_token=settings.jupyterhub_api_token,
    cache_max_age=60,
)


async def get_current_user(request: Request) -> User:
    # cookie = request.cookies.get(auth.cookie_name)
    cookie = None  # TODO: jupyterhub 2.0 compat
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


def get_k8s_api() -> Tuple[kubernetes.client.CoreV1Api, kubernetes.client.BatchV1Api]:
    kubernetes.config.load_config()

    return kubernetes.client.CoreV1Api(), kubernetes.client.BatchV1Api()


# ----------------------------------------------------------------------------
# app

# cronjobs #
@router.get("/cronjobs/{job_name}")
async def read_cronjob(job_name: str, user: User = Depends(get_current_user)):
    return _perform_action(job_name, user.namespace, "read", V1CronJob)


@router.get("/cronjobs/")
async def read_cronjobs(user: User = Depends(get_current_user)):
    return _perform_action(None, user.namespace, "list", V1CronJob)


@router.delete("/cronjobs/{job_name}")
async def delete_cronjob(job_name: str, user: User = Depends(get_current_user)):
    return _perform_action(job_name, user.namespace, "delete", V1CronJob)


@router.post("/cronjobs/")
async def create_cronjob(request: Request, user: User = Depends(get_current_user)):
    data = await request.json()
    return _create_job(data, V1CronJob, user)


# jobs #
@router.get("/jobs/{job_name}")
async def read_job(job_name: str, user: User = Depends(get_current_user)):
    return _perform_action(job_name, user.namespace, "read", V1Job)


@router.get("/jobs/")
async def read_jobs(user: User = Depends(get_current_user)):
    return _perform_action(None, user.namespace, "list", V1Job)


@router.delete("/jobs/{job_name}")
async def delete_job(job_name: str, user: User = Depends(get_current_user)):
    return _perform_action(job_name, user.namespace, "delete", V1Job)


@router.post("/jobs/")
async def create_job(request: Request, user: User = Depends(get_current_user)):
    data = await request.json()
    return _create_job(data, V1Job, user)


# pods #
@router.get("/pods/{pod_name}")
async def read_pod(pod_name: str, user: User = Depends(get_current_user)):
    core_api, _ = get_k8s_api()
    result = core_api.read_namespaced_pod(pod_name, namespace=user.namespace)
    return result.to_dict()


@router.get("/pods/")
async def read_pods(
    user: User = Depends(get_current_user), job_name: Optional[str] = None
):
    core_api, _ = get_k8s_api()
    kwargs = {}

    if job_name:
        kwargs["label_selector"] = f"job-name={job_name}"
    result = core_api.list_namespaced_pod(user.namespace, **kwargs)
    return result.to_dict()


@router.get("/jobs/logs/{pod_name}/", response_class=Response)
async def logs(
    pod_name: str,
    user: User = Depends(get_current_user),
    stream: Optional[bool] = False,
):
    core_api, _ = get_k8s_api()
    if stream:
        w = kubernetes.watch.Watch()
        source = iter(
            w.stream(
                core_api.read_namespaced_pod_log,
                name=pod_name,
                namespace=user.namespace,
            )
        )
        return StreamingResponse(source)
    else:
        logs = core_api.read_namespaced_pod_log(name=pod_name, namespace=user.namespace)
        return logs


@router.get("/profiles/")
async def profiles():
    return profile_data


@router.get("/")
def get_root():
    logger.info("get-router")
    return {"message": "kbatch"}


@router.get("/authorized")
def authorized(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(**user.dict())


app.include_router(router)


if settings.kbatch_prefix:

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


def _create_job(
    data: dict,
    model: Union[V1CronJob, V1Job],
    user: User = Depends(get_current_user),
):
    """
    Create a Kubernetes batch Job or CronJob.

    This is handled in three steps:
    1. Submit ConfigMap
    2. Submit Job/CronJob
    3. Patch ConfigMap to add Job/CronJob as the owner

    Parameters
    ----------
    data : data specific to the Job or CronJob.
    model : kubernetes batch models, "V1Job" "V1CronJob".
    user : a `User` object which holds specific configuration settings.
    """
    api, batch_api = get_k8s_api()

    job_data = data["job"]

    # does it handle cronjob job specs appropriately?
    if job_template:
        job_data = utils.merge_json_objects(job_data, job_template)

    # can be either job or cronjob
    job = utils.parse(job_data, model=model)
    job_to_patch = job

    if issubclass(model, V1CronJob):
        j = job_data.get("spec", {}).get("job_template", {})
        job_to_patch = utils.parse(j, V1Job)

    code_data = data.get("code", None)
    if code_data:
        # The contents were base64encoded prior to being JSON serialized
        # we have to decode it *after* submitting things to the API server...
        # This is not great.
        # code_data["binary_data"]["code"] = base64.b64decode(code_data["binary_data"]["code"])
        config_map: Optional[V1ConfigMap] = utils.parse(code_data, model=V1ConfigMap)
    else:
        config_map = None

    patch.patch(
        job_to_patch,
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
    if settings.kbatch_create_user_namespace:
        logger.info("Ensuring namespace %s", user.namespace)
        created = ensure_namespace(api, user.namespace)
        if created:
            logger.info("Created namespace %s", user.namespace)

    if config_map:
        logger.info("Submitting ConfigMap")
        config_map = api.create_namespaced_config_map(
            namespace=user.namespace, body=config_map
        )
        patch.add_submitted_configmap_name(job, config_map)

    logger.info("Submitting job")
    try:
        if issubclass(model, V1Job):
            resp = batch_api.create_namespaced_job(namespace=user.namespace, body=job)
        elif issubclass(model, V1CronJob):
            resp = batch_api.create_namespaced_cron_job(
                namespace=user.namespace, body=job
            )

    except kubernetes.client.exceptions.ApiException as e:
        content_type = e.headers.get("Content-Type")
        if content_type:
            headers = {"Content-Type": content_type}
        else:
            headers = {}
        raise HTTPException(status_code=e.status, detail=e.body, headers=headers)

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


def _perform_action(
    job_name: Union[str, None],
    namespace: str,
    action: str,
    model: Union[V1Job, V1CronJob],
) -> str:
    """
    Perform an action on `job_name`.

    Parameters
    ----------
    job_name : name of the Kubernetes Job or CronJob.
    namespace : Kubernetes namespace to check.
    action : action to perform on `job_name`.
        Must match one item in `job_actions` list.
    model : kubernetes batch models, "V1Job" "V1CronJob"
    """
    job_actions = ["list", "read", "delete"]
    if action not in job_actions:
        raise ValueError(
            f"Unknown `action` specified: {action}. "
            + "Please select from one of the following: {job_actions}."
        )

    if issubclass(model, V1Job):
        model = "job"
    elif issubclass(model, V1CronJob):
        model = "cron_job"

    _, batch_api = get_k8s_api()
    f = getattr(batch_api, f"{action}_namespaced_{model}")

    if action == "list":
        return f(namespace).to_dict()
    else:
        return f(job_name, namespace).to_dict()
