import os
from typing import List

from pydantic import BaseSettings


class Settings(BaseSettings):
    kbatch_database_url: str
    kbatch_service_prefix: str = "/services/kbatch"
    kbatch_namespace: str = "default"

    kbatch_job_resources: ...
    kbatch_job_tolerations: List[str]

    jupyterhub_api_token: str
    jupyterhub_service_prefix: str = "/"

    class Config:
        env_file = os.environ.get("KBATCH_SETTINGS_PATH", ".env")
        env_file_encoding = "utf-8"
