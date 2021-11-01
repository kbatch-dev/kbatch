import pathlib

import httpx

import kbatch


HERE = pathlib.Path(__file__).parent


def mock_upload(request):
    return httpx.Response(
        201,
        json={
            "url": "https://example.org/kbatch/uploads/1/",
        },
    )


def mock_job(request):
    data = {
        "url": "http://example.org/kbatch/jobs/1/",
        "command": ["sh", "script.sh"],
        "image": "mcr.microsoft.com/planetary-computer/python",
        "name": "my-job",
        "description": None,
        "env": {"MY_KEY": "value"},
        "user": "taugspurger",
        "upload": "http://example.org/kbatch/uploads/1/",
    }

    return httpx.Response(201, json=data)


def test_submit_script(respx_mock):
    respx_mock.post("https://example.org/kbatch/uploads/").mock(side_effect=mock_upload)
    respx_mock.post("https://example.org/kbatch/jobs/").mock(side_effect=mock_job)

    spec = kbatch.Job(
        name="my-job",
        args=None,
        code=HERE / "examples/file/main.py",
        command=["python", "main.py"],
        description=None,
        image="mcr.microsoft.com/planetary-computer/python:latest",
        env={"MY_KEY": "value"},
    )

    result = kbatch.submit_job(spec, kbatch_url="https://example.org/kbatch/")
    expected = {
        "url": "http://example.org/kbatch/jobs/1/",
        "command": ["sh", "script.sh"],
        "image": "mcr.microsoft.com/planetary-computer/python",
        "name": "my-job",
        "description": None,
        "env": {"MY_KEY": "value"},
        "user": "taugspurger",
        "upload": "http://example.org/kbatch/uploads/1/",
    }

    # not really testing much here :/
    assert result == expected
