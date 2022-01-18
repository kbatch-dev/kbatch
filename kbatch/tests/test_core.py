import json
import contextlib
import io
import os
import pathlib
import zipfile

import httpx
import respx
import pytest
import kubernetes

import kbatch

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def model_job():
    return kbatch.Job(name="name", command=["ls -lh"], image="alpine")


@pytest.mark.parametrize(
    "env",
    [
        {"KEY1": "VALUE1", "KEY2": "VALUE2"},
    ],
)
def test_env(env):
    jobin = kbatch.Job(name="name", command=["ls -lh"], image="alpine", env=env)

    job = kbatch.make_job(jobin)
    container = job.spec.template.spec.containers[0]
    assert container.env == [
        kubernetes.client.V1EnvVar(name="KEY1", value="VALUE1"),
        kubernetes.client.V1EnvVar(name="KEY2", value="VALUE2"),
    ]


def test_command_args():
    model_job = kbatch.Job(
        name="name",
        command=["/bin/sh"],
        args=["-c", "python"],
        image="alpine",
    )
    job = kbatch.make_job(model_job)

    job_container = job.spec.template.spec.containers[0]
    assert job_container.args == ["-c", "python"]
    assert job_container.command == ["/bin/sh"]


@pytest.mark.parametrize("as_dir", [True, False])
def test_make_configmap(tmp_path: pathlib.Path, as_dir: bool):
    p = tmp_path / "file.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("ls")

    if as_dir:
        result = kbatch._backend.make_configmap(p.parent, generate_name="test")
    else:
        result = kbatch._backend.make_configmap(p, generate_name="test")

    assert result.api_version == "v1"
    assert list(result.binary_data) == ["code"]
    assert zipfile.is_zipfile(io.BytesIO(result.binary_data["code"]))
    assert result.metadata.generate_name == "test"

    if as_dir:
        assert b"file.txt" in result.binary_data["code"]
    else:
        assert b"ls" in result.binary_data["code"]


@contextlib.contextmanager
def tmp_env(key, value):
    original = os.environ.get(key, None)
    try:
        os.environ[key] = value
        yield
    finally:
        if original is None:
            del os.environ[key]
        else:
            os.environ[key] = original


def test_handle_url():
    config = {"kbatch_url": "http://kbatch-config.com/"}
    result = kbatch._core.handle_url("http://kbatch.com/", config)
    assert result == "http://kbatch.com/"

    result = kbatch._core.handle_url("http://kbatch.com", config)
    assert result == "http://kbatch.com/"

    with tmp_env("KBATCH_URL", "http://kbatch-env.com/"):
        result = kbatch._core.handle_url(None, config)
        assert result == "http://kbatch-env.com/"

        result = kbatch._core.handle_url("http://kbatch.com/", config)
        assert result == "http://kbatch.com/"

    result = kbatch._core.handle_url(None, config)
    assert result == "http://kbatch-config.com/"

    with pytest.raises(ValueError, match="Must specify"):
        kbatch._core.handle_url(None, config={"kbatch_url": None})


# These tests mock out the server component. They aren't really testing much.


def test_configure(respx_mock: respx.MockRouter, tmp_path: pathlib.Path):
    respx_mock.get("http://kbatch.com/authorized").mock(
        return_value=httpx.Response(200)
    )

    expected = tmp_path / "kbatch/config.json"
    with tmp_env("XDG_CONFIG_HOME", str(tmp_path)):
        result = kbatch._core.config_path()
        assert result == expected

        result = kbatch._core.configure(kbatch_url="http://kbatch.com", token="abc")
        assert result == expected

    config = json.loads(expected.read_text())
    assert config == {"token": "abc", "kbatch_url": "http://kbatch.com/"}


def test_show_job(respx_mock: respx.MockRouter):
    data = json.loads(HERE.joinpath("data", "show_job.json").read_text())
    respx_mock.get("http://kbatch.com/jobs/myjob").mock(
        return_value=httpx.Response(200, json=data)
    )

    result = kbatch.show_job("myjob", "http://kbatch.com/", token="abc")
    assert result == data


def test_list_jobs(respx_mock: respx.MockRouter):
    data = json.loads(HERE.joinpath("data", "list_jobs.json").read_text())
    respx_mock.get("http://kbatch.com/jobs/").mock(
        return_value=httpx.Response(200, json=data)
    )

    result = kbatch.list_jobs("http://kbatch.com/", token="abc")
    assert result == data


def test_list_pods(respx_mock: respx.MockRouter):
    data = json.loads(HERE.joinpath("data", "list_pods.json").read_text())
    respx_mock.get("http://kbatch.com/pods/").mock(
        return_value=httpx.Response(200, json=data)
    )

    result = kbatch.list_pods("http://kbatch.com/", token="abc")
    assert result == data


def test_logs(respx_mock: respx.MockRouter):
    data = HERE.joinpath("data", "list_jobs.json").read_text()
    respx_mock.get("http://kbatch.com/jobs/logs/mypod/").mock(
        return_value=httpx.Response(200, text=data)
    )

    result = kbatch.logs("mypod", "http://kbatch.com/", token="abc")
    assert result == data


def test_logs_streaming(respx_mock: respx.MockRouter):
    data = HERE.joinpath("data", "list_jobs.json").read_text()
    respx_mock.get("http://kbatch.com/jobs/logs/mypod/").mock(
        return_value=httpx.Response(200, text=data)
    )

    buffers = []
    gen = kbatch.logs_streaming("mypod", "http://kbatch.com/", token="abc")
    for batch in gen:
        buffers.append(batch)
    result = "".join(buffers)
    assert result == data


def test_submit_job(respx_mock: respx.MockRouter):
    respx_mock.post("http://kbatch.com/jobs/").mock(
        return_value=httpx.Response(200, json={"mock": "response"})
    )

    job = kbatch.Job(
        name="name",
        command=["/bin/sh"],
        args=["-c", "python"],
        image="alpine",
    )

    result = kbatch.submit_job(job, kbatch_url="http://kbatch.com/", token="abc")
    assert result

    job = kbatch.Job(
        name="name",
        command=["/bin/sh"],
        args=["-c", "python"],
        image="alpine",
    )

    result = kbatch.submit_job(
        job, code=__file__, kbatch_url="http://kbatch.com/", token="abc"
    )
    assert result
