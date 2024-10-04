"""
These tests require access to the Kubernetes API.
Starting a basic k3d cluster is the simpliest way to get started.
See the documentation's "Dev Guide" for more information.
"""

import json
import pathlib

import kbatch_proxy.main
from kubernetes.client.models import V1Job

HERE = pathlib.Path(__file__).parent


def test_create_job():
    username = "some_name"
    user = kbatch_proxy.main.User(name=username, groups=[], api_token="xyz")

    file = HERE / "data/incoming_job.json"
    with open(file) as fp:
        incoming_job_data = json.load(fp)

    job = kbatch_proxy.main._create_job(incoming_job_data, V1Job, user)

    assert job["metadata"]["annotations"]["kbatch.jupyter.org/username"] == username
    # test that `code` input has been added to the job
    assert job["spec"]["template"]["spec"]["init_containers"]
