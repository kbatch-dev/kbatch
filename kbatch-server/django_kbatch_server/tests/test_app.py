"""
Do these tests mock the backend? I think so...
"""
import pathlib
import uuid
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient


client = APIClient()

USERNAME = "taugspurger"
AUTH_HEADER = {"HTTP_AUTHORIZATION": "token abc"}


def authenticate_side_effect(token):
    if token == "abc":
        return dict(name=USERNAME, groups=[])


@pytest.fixture
def mock_hub(mocker):
    yield mocker.patch(
        "django_kbatch_server.authentication.auth.user_for_token",
        autospec=True,
        side_effect=authenticate_side_effect,
    )


@pytest.fixture
def mock_backend(mocker):
    yield mocker.patch("django_kbatch_server.models.backend")


@pytest.mark.usefixtures("mock_hub", "mock_backend")
@pytest.mark.django_db
class TestKBatch:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/services/kbatch/")
        assert response.status_code == 200

    def test_list_jobs_unauthenticated(self):
        response = client.get("/services/kbatch/jobs/")
        assert response.status_code == 401

        job_name = f"test-job-{uuid.uuid1()}"

        data = {"command": ["ls", "-lh"], "image": "alpine", "name": job_name}
        response = client.post(
            "/services/kbatch/jobs/",
            data,
        )
        assert response.status_code == 401

    def test_list_jobs(self):
        response = client.get("/services/kbatch/jobs/", **AUTH_HEADER)
        assert response.status_code == 200
        assert response.json() == {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [],
        }

        job_name = f"test-job-{uuid.uuid1()}"
        data = {"command": ["ls", "-lh"], "image": "alpine", "name": job_name}
        response = client.post(
            "/services/kbatch/jobs/",
            data,
            format="json",
            **AUTH_HEADER,
        )
        assert response.status_code == 201
        result = response.json()
        assert result.pop("user") == USERNAME
        assert result.pop("upload") is None
        assert result.pop("env") is None
        url = result.pop("url")
        assert url.startswith("http://testserver/services/kbatch/jobs/")

        assert result == data

    def test_post_file(self, tmp_path: pathlib.Path):

        p = tmp_path / "file.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("ls")
        zp = p.parent.with_suffix(".zip")

        with zipfile.ZipFile(zp, mode="w") as zf:
            zf.write(p)

        file = SimpleUploadedFile(
            "file.txt", zp.read_bytes(), content_type="application/zip"
        )

        response = client.post(
            "/services/kbatch/uploads/",
            {"file": file},
            format="multipart",
            **AUTH_HEADER,
        )
        assert response.status_code == 201
        result = response.json()

        response = client.post(
            "/services/kbatch/jobs/",
            {"upload": result["url"], "name": f"test-{uuid.uuid1()}"},
            format="json",
            **AUTH_HEADER,
        )
        assert response.status_code == 201
        assert response.json()["upload"] == result["url"]

    def test_post_upload_data(self):
        data = {
            "name": f"test-{uuid.uuid1()}",
            "upload_data": "ls -lh",
        }
        response = client.post(
            "/services/kbatch/jobs/", data, format="json", **AUTH_HEADER
        )
        assert response.status_code == 201
        result = response.json()

        assert result.pop("command") is None
        assert result.pop("env") is None
        assert result.pop("image") == "alpine"
        assert result.pop("upload")
        assert result.pop("url")
        assert result.pop("user") == USERNAME
        assert result["name"] == data["name"]
        assert "uploaded_data" not in response

    def test_requires_zip(self, tmp_path: pathlib.Path):
        p = tmp_path / "file.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("ls")

        file = SimpleUploadedFile("file.txt", b"abc", content_type="text/plain")

        response = client.post(
            "/services/kbatch/uploads/",
            {"file": file},
            format="multipart",
            **AUTH_HEADER,
        )
        assert response.status_code == 400
        assert response.json() == {
            "file": ["The submitted file must be a ZIP archive."]
        }
