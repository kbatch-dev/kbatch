import os
import json
from pathlib import Path
from typing import Mapping, Optional, List

import httpx
import urllib.parse


def configure(jupyterhub_url=None, kbatch_url=None, token=None):
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN")
    jupyterhub_url = jupyterhub_url or os.environ.get("JUPYTERHUB_API_URL")
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL")

    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    client = httpx.Client()

    headers = {"Authorization": f"token {token}"}
    # verify that things are OK
    # TODO: flexible URL
    breakpoint()
    r = client.get(
        urllib.parse.urljoin(jupyterhub_url, f"authorizations/token/{token}"),
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get(kbatch_url, headers=headers)
    assert r.status_code == 200

    config = {"url": kbatch_url, "token": token}

    config_home = (
        os.environ.get("APPDATA")
        or os.environ.get("XDG_CONFIG_HOME")
        or (os.path.join(os.environ.get("HOME", ""), ".config"))
    )
    configpath = Path(config_home) / "kbatch/config.json"

    configpath.parent.mkdir(exist_ok=True, parents=True)
    configpath.write_text(json.dumps(config))


def list(url, token):
    client = httpx.Client()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN")

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(urllib.parse.urljoin(url, "jobs/"), headers=headers)
    if r.status_code >= 201:
        raise ValueError(r.json())

    return r.json()


def submit(
    name: str,
    image: str,
    command: List[str],
    file: str,
    url: str,
    token: str,
    env: Optional[Mapping[str, str]],
):
    client = httpx.Client()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN")

    headers = {
        "Authorization": f"token {token}",
    }

    data = {"image": image, "name": name, "command": command, "env": env}

    if file:
        r = client.post(
            urllib.parse.urljoin(url, "uploads/"),
            files={"file": open(file, "rb")},
            headers=headers,
        )
        if r.status_code > 201:
            raise ValueError(r.json())

        data["upload"] = r.json()["url"]

    r = client.post(
        urllib.parse.urljoin(url, "jobs/"),
        json=data,
        headers=headers,
    )
    assert r.status_code == 201

    return r.json()
