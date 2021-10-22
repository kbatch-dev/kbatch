import os
from typing import Mapping, Optional, List

import httpx
import urllib.parse


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
