import functools
import shlex
import uuid
from typing import List, Union,  Optional
from urllib.parse import quote

import databases
import sqlalchemy
import jupyterhub.services.auth
from fastapi import FastAPI, APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, BaseSettings


from . import backend
from .config import Settings


settings = Settings()

# ----------------------------------------------------------------------------
# Database configuration
database = databases.Database(settings.kbatch_database_url)
metadata = sqlalchemy.MetaData()

jobs = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("command", sqlalchemy.String), 
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
# Models


class JobIn(BaseModel):
    command: List[str]
    image: str


class Job(BaseModel):
    id: int
    command: List[str]
    image: str
    username: str


class User(BaseModel):
    authenticated: bool
    redirect_url: Optional[str]
    name: Optional[str]
    groups: Optional[List[str]]


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
async def create_job(job: JobIn, user: User = Depends(get_current_user), k8s_api = Depends(get_k8s_api)):
    if not user.authenticated:
        return RedirectResponse(user.redirect_url)

    query = jobs.insert().values(
        command=" ".join(job.command),
        image=job.image,
        username=user.name
    )
    last_record_id = await database.execute(query)
    name = str(uuid.uuid1())

    k8s_job = backend.make_job(
        cmd=job.command,
        image=job.image,
        name=name,  # TODO: accept a name / generate.
        username=user.name,
    )
    resp = await backend.submit_job(k8s_api, k8s_job)
    print(resp)

    return {**job.dict(), "id": last_record_id, "username": user.name}


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

