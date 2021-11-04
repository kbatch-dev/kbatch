import pytest
from fastapi.testclient import TestClient

from kbatch_proxy.main import app

client = TestClient(app)


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
