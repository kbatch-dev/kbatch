import os
from typing import List, Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    kbatch_database_url: str
    kbatch_service_prefix: str = "/services/kbatch"
    kbatch_namespace: str = "default"

    kbatch_job_cpu_guarantee: Optional[str] = None
    kbatch_job_cpu_limit: Optional[str] = None
    kbatch_job_mem_guarantee: Optional[str] = None
    kbatch_job_mem_limit: Optional[str] = None

    kbatch_job_tolerations: Optional[List[str]]

    jupyterhub_api_token: str
    jupyterhub_service_prefix: str = "/"

    class Config:
        env_file = os.environ.get("KBATCH_SETTINGS_PATH", ".env")
        env_file_encoding = "utf-8"
