import datetime
import base64
import os
import json
from pathlib import Path
from typing import Optional, Dict, Union

import rich.table
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


def handle_url(kbatch_url: Optional[str], config: Dict[str, Optional[str]]) -> str:
    """
    Resolve the URL, with the following order:

    1. The argument
    2. The environment variable
    3. The value from the config
    """
    kbatch_url = kbatch_url or os.environ.get("KBATCH_URL") or config["kbatch_url"]
    if not kbatch_url:
        raise ValueError(
            "Must specify 'kbatch_url' or set the 'KBATCH_URL' environment variable."
        )
    if not kbatch_url.endswith("/"):
        kbatch_url += "/"

    return kbatch_url


def configure(kbatch_url=None, token=None) -> Path:
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN")
    kbatch_url = handle_url(kbatch_url, config={"kbatch_url": None})

    client = httpx.Client(follow_redirects=True)

    headers = {"Authorization": f"token {token}"}
    # verify that things are OK
    # TODO: flexible URL

    url = urllib.parse.urljoin(kbatch_url, "authorized")
    r = client.get(url, headers=headers)
    r.raise_for_status()

    config = {"kbatch_url": kbatch_url, "token": token}
    configpath = config_path()

    configpath.parent.mkdir(exist_ok=True, parents=True)
    configpath.write_text(json.dumps(config))
    return configpath


def show_job(job_name, kbatch_url, token):
    client = httpx.Client(follow_redirects=True)
    config = load_config()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = handle_url(kbatch_url, config)

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(
        urllib.parse.urljoin(kbatch_url, f"jobs/{job_name}"), headers=headers
    )
    r.raise_for_status()

    return r.json()


def list_jobs(kbatch_url, token):
    client = httpx.Client(follow_redirects=True)
    config = load_config()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = handle_url(kbatch_url, config)

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(urllib.parse.urljoin(kbatch_url, "jobs/"), headers=headers)
    r.raise_for_status()

    return r.json()


def list_pods(kbatch_url: str, token: Optional[str], job_name: Optional[str] = None):
    client = httpx.Client(follow_redirects=True)
    config = load_config()

    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = handle_url(kbatch_url, config)

    headers = {
        "Authorization": f"token {token}",
    }

    r = client.get(
        urllib.parse.urljoin(kbatch_url, "pods/"),
        headers=headers,
        params=dict(job_name=job_name),
    )
    r.raise_for_status()

    return r.json()


def logs(pod_name, kbatch_url, token, read_timeout: int = 60):
    gen = _logs(pod_name, kbatch_url, token, stream=False, read_timeout=read_timeout)
    result = next(gen)
    return result


def logs_streaming(pod_name, kbatch_url, token, read_timeout: int = 60):
    return _logs(pod_name, kbatch_url, token, stream=True, read_timeout=read_timeout)


def _logs(
    pod_name, kbatch_url, token, stream: Optional[bool] = False, read_timeout: int = 60
):
    config = load_config()
    client = httpx.Client(
        follow_redirects=True, timeout=httpx.Timeout(5, read=read_timeout)
    )
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = handle_url(kbatch_url, config)

    headers = {
        "Authorization": f"token {token}",
    }

    if stream:
        with client.stream(
            "GET",
            urllib.parse.urljoin(kbatch_url, f"jobs/logs/{pod_name}/"),
            headers=headers,
            params=dict(stream=stream),
        ) as r:
            for data in r.iter_text():
                yield data

    else:
        r = client.get(
            urllib.parse.urljoin(kbatch_url, f"jobs/logs/{pod_name}/"),
            headers=headers,
        )
        r.raise_for_status()

        yield r.text


def submit_job(
    job: Job,
    *,
    code: Optional[Union[str, Path]] = None,
    kbatch_url: Optional[str] = None,
    token: Optional[str] = None,
    profile: Optional[dict] = None,
):
    from ._backend import make_job

    config = load_config()

    client = httpx.Client(follow_redirects=True)
    token = token or os.environ.get("JUPYTERHUB_API_TOKEN") or config["token"]
    kbatch_url = handle_url(kbatch_url, config)

    headers = {
        "Authorization": f"token {token}",
    }
    # data = job.to_kubernetes().to_dict()
    profile = profile or {}
    data = make_job(job, profile=profile).to_dict()
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
    r.raise_for_status()

    return r.json()


def status(row):
    if row["status"]["succeeded"]:
        return "[green]done[/green]"
    elif row["status"]["failed"]:
        return "[red]failed[/red]"
    elif row["status"]["active"]:
        return "active"
    else:
        raise ValueError


def pod_status(row):
    return row["status"]["phase"]


def duration(row):
    start_time = datetime.datetime.fromisoformat(row["status"]["start_time"])
    end_time: Optional[datetime.timedelta] = None

    if row["status"]["succeeded"]:
        end_time = datetime.datetime.fromisoformat(row["status"]["completion_time"])
    elif row["status"]["failed"]:
        end_time = None
    else:
        end_time = datetime.datetime.now(tz=datetime.timezone.utc)

    if end_time:
        duration = end_time - start_time
        # round for formatting
        duration = duration - datetime.timedelta(microseconds=duration.microseconds)
    else:
        duration = "-"
    return str(duration)


def format_jobs(data):
    table = rich.table.Table(title="Jobs")

    table.add_column("job name", style="bold", no_wrap=True)
    table.add_column("submitted")
    table.add_column("status")
    table.add_column("duration")

    for row in data["items"]:
        table.add_row(
            row["metadata"]["name"],
            row["metadata"]["creation_timestamp"],
            status(row),
            duration(row),
        )

    return table


def format_pods(data):
    table = rich.table.Table(title="Pods")

    table.add_column("pod name", style="bold", no_wrap=True)
    table.add_column("submitted")
    table.add_column("status")
    # table.add_column("duration")

    for row in data["items"]:
        table.add_row(
            row["metadata"]["name"],
            row["metadata"]["creation_timestamp"],
            pod_status(row),
            # duration(row),
        )

    return table


def show_profiles(kbatch_url):
    client = httpx.Client(follow_redirects=True)
    config = load_config()

    kbatch_url = handle_url(kbatch_url, config)

    url = urllib.parse.urljoin(kbatch_url, "profiles/")
    r = client.get(url)
    r.raise_for_status()

    return r.json()


def load_profile(profile_name: str, kbatch_url: str) -> dict:
    profiles = show_profiles(kbatch_url)
    profile = profiles[profile_name]
    return profile
