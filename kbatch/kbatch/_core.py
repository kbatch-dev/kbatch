import base64
import os
import json
from pathlib import Path
from typing import Optional, Dict, Union

import httpx
import urllib.parse

from ._types import Job
from ._backend import make_configmap


def config_path() -> Path:
    config_home = (
        os.environ.get("APPDATA")
        or os.environ.get("XDG_CONFIG_HOME")
        or (os.path.join(os.environ.get("HOME", ""), ".config"))
    )
    return Path(config_home) / "kbatch/config.json"


def load_config() -> Dict[str, Optional[str]]:
    p = config_path()
    config: Dict[str, Optional[str]] = {"token": None, "kbatch_url": None}
    if p.exists():
        with open(config_path()) as f:
            config = json.load(f)
    return config


def configure(kbatch_url=None, token=None) -> Path:
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN")
    # Add an authorization endpoint to kbatch, have that
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL")
    # TODO: find the hub API url from a url..

    if not kbatch_url:
        raise ValueError(
            "Must specify 'kbatch_url' or set the 'KBATCH_URL' environment variable."
        )

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    client = httpx.Client(follow_redirects=True)

    headers = {"Authorization": f"token {token}"}
    # verify that things are OK
    # TODO: flexible URL

    url = urllib.parse.urljoin(kbatch_url, "authorized")
    r = client.get(url, headers=headers)
    assert r.status_code == 200

    config = {"kbatch_url": kbatch_url, "token": token}
    configpath = config_path()

    configpath.parent.mkdir(exist_ok=True, parents=True)
    configpath.write_text(json.dumps(config))
    return configpath


def show_job(job_name, kbatch_url, token):
    client = httpx.Client(follow_redirects=True)
    config = load_config()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL") or config["kbatch_url"]

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(
        urllib.parse.urljoin(kbatch_url, f"jobs/{job_name}"), headers=headers
    )
    if r.status_code >= 399:
        raise ValueError(r.json())

    return r.json()


def list_jobs(kbatch_url, token):
    client = httpx.Client(follow_redirects=True)
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
    job: Job,
    *,
    code: Optional[Union[str, Path]] = None,
    kbatch_url: Optional[str] = None,
    token: Optional[str] = None,
):
    config = load_config()

    client = httpx.Client(follow_redirects=True)
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL") or config["kbatch_url"]

    if kbatch_url is None:
        raise ValueError(...)

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    headers = {
        "Authorization": f"token {token}",
    }
    data = job.to_kubernetes().to_dict()
    data = {"job": data}
    if code:
        cm = make_configmap(code, generate_name=job.name).to_dict()
        cm["binary_data"]["code"] = base64.b64encode(cm["binary_data"]["code"]).decode(
            "ascii"
        )
        data["code"] = cm

    r = client.post(
        urllib.parse.urljoin(kbatch_url, "jobs/"),
        json=data,
        headers=headers,
    )
    if r.status_code >= 400:
        raise ValueError(r.json())

    return r.json()


def logs(job_name, kbatch_url, token):
    config = load_config()

    client = httpx.Client(follow_redirects=True)
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL") or config["kbatch_url"]

    if kbatch_url is None:
        raise ValueError(...)

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(
        urllib.parse.urljoin(kbatch_url, f"jobs/logs/{job_name}/"), headers=headers
    )
    return r.text
