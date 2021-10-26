import os
import zipfile
import shutil
import tempfile
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Optional, List, Dict

import httpx
import urllib.parse


@dataclass
class JobSpec:
    """
    Specification for a job.

    Parameters
    ----------
    code: str
        Relative path to a file or directory to upload and make available to the job.
    command : str
        The (perhaps multiline) command to run. This can rely on the file or directory
        `code` being available.
    image : str
    name : str
    description : str
    env : Mapping[str, str]
        Environment variables to make available.
    """

    code: Optional[str] = None
    args: Optional[List[str]] = None
    command: Optional[str] = None
    image: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)

    def to_json(self, include_code=False):
        if include_code:
            raise ValueError
        return {
            "command": self.command,
            "image": self.image,
            "name": self.name,
            "description": self.description,
            "env": self.env,
        }


def config_path() -> Path:
    config_home = (
        os.environ.get("APPDATA")
        or os.environ.get("XDG_CONFIG_HOME")
        or (os.path.join(os.environ.get("HOME", ""), ".config"))
    )
    return Path(config_home) / "kbatch/config.json"


def load_config() -> Dict[str, str]:
    p = config_path()
    config = {"token": None, "kbatch_url": None}
    if p.exists():
        with open(config_path()) as f:
            config = json.load(f)
    return config


def configure(jupyterhub_url=None, kbatch_url=None, token=None) -> Path:
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN")
    jupyterhub_url = jupyterhub_url or os.environ.get("JUPYTERHUB_API_URL")
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL")
    # TODO: find the hub API url from a url..

    if not jupyterhub_url:
        raise ValueError(
            "Must specify 'jupyterhub_url' or set the 'JUPYTERHUB_URL' environment variable."
        )

    if not kbatch_url:
        raise ValueError(
            "Must specify 'kbatch_url' or set the 'KBATCH_URL' environment variable."
        )

    if not jupyterhub_url.endswith("/"):
        jupyterhub_url += "/"

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    client = httpx.Client()

    headers = {"Authorization": f"token {token}"}
    # verify that things are OK
    # TODO: flexible URL
    url = urllib.parse.urljoin(jupyterhub_url, f"authorizations/token/{token}")
    r = client.get(
        url,
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get(kbatch_url, headers=headers)
    assert r.status_code == 200

    config = {"kbatch_url": kbatch_url, "token": token}
    configpath = config_path()

    configpath.parent.mkdir(exist_ok=True, parents=True)
    configpath.write_text(json.dumps(config))
    return configpath


def list_jobs(kbatch_url, token):
    client = httpx.Client()
    config = load_config()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL") or config["kbatch_url"]

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(urllib.parse.urljoin(kbatch_url, "jobs/"), headers=headers)
    if r.status_code >= 201:
        raise ValueError(r.json())

    return r.json()


def submit_job(
    spec: JobSpec,
    *,
    kbatch_url: Optional[str] = None,
    token: Optional[str] = None,
):
    config = load_config()

    client = httpx.Client()
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL") or config["kbatch_url"]

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    headers = {
        "Authorization": f"token {token}",
    }

    data = spec.to_json()

    if spec.code:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "code"
            if Path(spec.code).is_dir():
                archive = shutil.make_archive(p, "zip", spec.code)
            else:
                archive = str(p.with_suffix(".zip"))
                with zipfile.ZipFile(archive, mode="w") as zf:
                    zf.write(spec.code)

            r = client.post(
                urllib.parse.urljoin(kbatch_url, "uploads/"),
                files={"file": open(archive, "rb")},
                headers=headers,
            )
            if r.status_code > 201:
                raise ValueError(r.json())

        data["upload"] = r.json()["url"]

    r = client.post(
        urllib.parse.urljoin(kbatch_url, "jobs/"),
        json=data,
        headers=headers,
    )
    assert r.status_code == 201

    return r.json()
