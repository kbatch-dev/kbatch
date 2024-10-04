import os

import pytest
from fastapi.testclient import TestClient
from kubernetes.config import list_kube_config_contexts

# make sure this happens before kbatch_proxy.main is imported
os.environ["kbatch_init_logging"] = "0"


@pytest.fixture(scope="session", autouse=True)
def check_cluster():
    """Make sure we don't accidentally run tests against a real cluster"""

    if os.getenv("CI") and "KBATCH_TEST_CONTEXT" not in os.environ:
        return

    test_context = os.environ.get("KBATCH_TEST_CONTEXT", "k3d-kbatch")
    _contexts, current_context = list_kube_config_contexts()
    current = current_context["name"]
    if current != test_context:
        raise RuntimeError(
            f"Refusing to run kbatch integration tests in {current} "
            f"!= KBATCH_TEST_CONTEXT={test_context}."
            f" Set $KBATCH_TEST_CONTEXT={current} if this is what you want."
        )


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

    # env patch must be before module patch to avoid logging setup
    mocker.patch.dict(
        os.environ,
        {
            "kbatch_init_logging": "0",
            "JUPYTERHUB_SERVICE_NAME": "kbatch",
        },
    )
    mocker.patch("kbatch_proxy.main.auth.user_for_token", side_effect=side_effect)


@pytest.fixture
def client(mock_hub_auth, mocker):
    # import kbatch_proxy.main must be after mock_hub_auth
    from kbatch_proxy.main import app

    client = TestClient(app)
    mocker.patch.dict(
        os.environ,
        {
            "KBATCH_URL": str(client.base_url),
            "JUPYTERHUB_API_TOKEN": "abc",
        },
    )
    return client


@pytest.fixture(autouse=True)
def kbatch_client(client, mocker):
    """Force kbatch cli to use TestClient"""
    mocker.patch("kbatch._core._client", side_effect=lambda **kwargs: client)
