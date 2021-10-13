import os
from typing import List, Union,  Optional
from urllib.parse import quote

import databases
import sqlalchemy
import jupyterhub.services.auth
from fastapi import FastAPI, APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# ----------------------------------------------------------------------------
# Database configuration
DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL)
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
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

# ----------------------------------------------------------------------------
# Jupyterhub configuration

prefix = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')
SERVICE_PREFIX = "/services/kbatch"

auth = jupyterhub.services.auth.HubAuth(
    api_token=os.environ['JUPYTERHUB_API_TOKEN'],
    cache_max_age=60,
)

# ----------------------------------------------------------------------------
# Models


class JobIn(BaseModel):
    user: str
    command: List[str]
    image: str
    user: str


class Job(BaseModel):
    id: int
    user: str
    status: str


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
        user = auth.user_for_token(token)
    else:
        user = None

    if user:
        return User(**user, authenticated=True)
    else:
        # redirect to login url on failed auth
        path = quote(request.url.path.removeprefix(SERVICE_PREFIX))
        print("auth.login_url", auth.login_url)
        # redirect isn't quite working in docker yet.
        return User(authenticated=False, redirect_url=auth.login_url + f'?next={path}')

# ----------------------------------------------------------------------------
# app

router = APIRouter()

@router.get("/jobs/{job_id}", response_model=List[Job])
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
    return await database.fetch_all(query)


@router.post("/jobs/", response_model=Job)
async def create_job(job: JobIn):
    query = jobs.insert().values(user=job.user, status=job.status)
    last_record_id = await database.execute(query)
    return {**job.dict(), "id": last_record_id}


@router.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}


app = FastAPI()
app.include_router(router, prefix=SERVICE_PREFIX)


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

