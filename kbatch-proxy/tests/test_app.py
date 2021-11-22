import sys
import pytest
import pathlib
import subprocess
from fastapi.testclient import TestClient

from kbatch_proxy.main import app

client = TestClient(app)

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def mock_hub_auth(mocker):
    def side_effect(token):
        if token == "abc":
            return {"name": "testuser", "groups": ["testgroup"]}

    mocker.patch("kbatch_proxy.main.auth.user_for_token", side_effect=side_effect)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "kbatch"}


@pytest.mark.usefixtures("mock_hub_auth")
def test_authorized():
    response = client.get("/authorized")
    assert response.status_code == 401

    response = client.get("/authorized", headers={"Authorization": "Token not-a-token"})
    assert response.status_code == 401

    response = client.get("/authorized", headers={"Authorization": "Token abc"})
    assert response.status_code == 200


def test_loads_profile():
    profile = str(HERE / "profile_template.yaml")
    code = "import asyncio; from kbatch_proxy.main import profiles; assert asyncio.run(profiles())"
    subprocess.check_output(
        f"KBATCH_PROFILE_FILE={profile} {sys.executable} -c '{code}'", shell=True
    )
