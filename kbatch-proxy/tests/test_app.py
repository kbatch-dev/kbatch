import os
import pathlib
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from kbatch_proxy.main import app

client = TestClient(app)

HERE = pathlib.Path(__file__).parent


@pytest.fixture(autouse=True)
def mock_hub_auth(mocker):
    def side_effect(token):
        if token == "abc":
            return {
                "name": "testuser",
                "groups": ["testgroup"],
                "scopes": ["access:services"],
            }
        elif token == "def":
            return {
                "name": "testuser2",
                "groups": [],
                "scopes": ["access:servers!user=testuser2"],
            }
        else:
            return None

    mocker.patch("kbatch_proxy.main.auth.user_for_token", side_effect=side_effect)
    mocker.patch.dict(os.environ, {"JUPYTERHUB_SERVICE_NAME": "kbatch"})


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "kbatch"}


def test_authorized(mock_hub_auth):
    response = client.get("/authorized")
    assert response.status_code == 401

    response = client.get("/authorized", headers={"Authorization": "Token not-a-token"})
    assert response.status_code == 401

    response = client.get("/authorized", headers={"Authorization": "token abc"})
    assert response.status_code == 200
    response = client.get("/authorized", headers={"Authorization": "Bearer abc"})
    assert response.status_code == 200

    response = client.get("/authorized", headers={"Authorization": "Bearer def"})
    assert response.status_code == 403


def test_loads_profile():
    profile = str(HERE / "profile_template.yaml")
    code = "import asyncio; from kbatch_proxy.main import profiles; assert asyncio.run(profiles())"
    subprocess.check_output(
        f"KBATCH_PROFILE_FILE={profile} {sys.executable} -c '{code}'", shell=True
    )
