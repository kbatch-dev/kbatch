import functools
import logging
import shlex
import uuid
from typing import List
from urllib.parse import quote

import databases
import sqlalchemy
import jupyterhub.services.auth
from fastapi import FastAPI, APIRouter, Request, Depends
from fastapi.responses import RedirectResponse


from . import backend
from .config import Settings
from .models import (
    Job,
    JobIn,
    User,
)


logger = logging.getLogger(__name__)



settings = Settings()

# ----------------------------------------------------------------------------
# Database configuration
database = databases.Database(settings.kbatch_database_url)
metadata = sqlalchemy.MetaData()

jobs = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String), 
    sqlalchemy.Column("command", sqlalchemy.String), 
    sqlalchemy.Column("script", sqlalchemy.String), 
    sqlalchemy.Column("image", sqlalchemy.String), 
    sqlalchemy.Column("username", sqlalchemy.String), 
)


engine = sqlalchemy.create_engine(
    settings.kbatch_database_url, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

# ----------------------------------------------------------------------------
# Jupyterhub configuration
# TODO: make auth pluggable

auth = jupyterhub.services.auth.HubAuth(
    api_token=settings.jupyterhub_api_token,
    cache_max_age=60,
)

# ----------------------------------------------------------------------------
# Kubernetes backend configuration
@functools.lru_cache
def get_k8s_api():
    return backend.make_api()


# ----------------------------------------------------------------------------
# auth
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl=auth.login)

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
        # redirect to login url on failed auth
        # TODO: Figure out how this interacts with --root-path
        path = quote(request.url.path)
        print("auth.login_url", auth.login_url)
        # redirect isn't quite working in docker yet.
        return User(authenticated=False, redirect_url=auth.login_url + f'?next={path}')

# ----------------------------------------------------------------------------
# app

router = APIRouter()

@router.get("/jobs/{job_id}", response_model=Job)
async def read_job(item_id: int, user: User = Depends(get_current_user)):
    if not user.authenticated:
        return RedirectResponse(user.redirect_url)

    query = jobs.select(id=item_id).where(jobs.c.username == user.name)
    return await database.fetch_one(query)



@router.get("/jobs/", response_model=List[Job])
async def read_jobs(user: User = Depends(get_current_user)):
    if not user.authenticated:
        return RedirectResponse(user.redirect_url)

    query = jobs.select().where(jobs.c.username == user.name)
    result = await database.fetch_all(query)
    result = [
        {"id": id_,
         "command": shlex.split(command),
         "image": image,
         "username": username,
         }
        for (id_, command, image, username) in result
    ]
    print(result)
    return result


@router.post("/jobs/", response_model=Job)
async def create_job(job: JobIn, user: User = Depends(get_current_user), k8s_apis = Depends(get_k8s_api)):
    if not user.authenticated:
        logger.info("User not authenticated for post.")
        return RedirectResponse(user.redirect_url)

    api, batch_api = k8s_apis

    command = job.command
    if command:
        # TODO(sqlite): sqlite doesn't support arrays.
        command = " ".join(command)

    if job.name is None:
        job.name = str(uuid.uuid1())

    query = jobs.insert().values(
        command=command,
        image=job.image,
        username=user.name
    )
    last_record_id = await database.execute(query)
    logger.info("Created job %d", last_record_id)

    job = Job(**{**job.dict(), "name": job.name, "id": last_record_id, "username": user.name})

    k8s_job, config_map = backend.make_job(
        job=job
    )
    logger.info("Submitting configmap for job %d", job.id)
    resp = await backend.submit_configmap(api, config_map)

    logger.debug("resp %s", resp)

    logger.info("Submitting job %d", job.id)
    resp = await backend.submit_job(batch_api, k8s_job)
    logger.debug("resp %s", resp)

    return job


@router.get("/")
async def root():
    return {"message": "kbatch"}


app = FastAPI()
app.include_router(router, prefix=settings.kbatch_service_prefix)


@app.get("/")
async def root():
    return {"message": "kbatch"}


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

