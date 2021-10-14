from pydantic import BaseSettings


class Settings(BaseSettings):
    kbatch_database_url: str
    kbatch_service_prefix: str = "/services/kbatch"
    jupyterhub_api_token: str
    jupyterhub_service_prefix: str = "/"