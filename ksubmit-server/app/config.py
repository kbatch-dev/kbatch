import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    kbatch_database_url: str
    kbatch_service_prefix: str = "/services/kbatch"
    jupyterhub_api_token: str
    jupyterhub_service_prefix: str = "/"

    class Config:
        env_file = os.environ.get("KBATCH_SETTINGS_PATH", ".env")
        env_file_encoding = "utf-8"