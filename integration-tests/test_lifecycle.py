"""
Test the lifecycle of a kbatch job

run fully through the CLI
"""

import json
import sys
import time

import pytest
from click.testing import CliRunner

from kbatch.cli import cli


@pytest.fixture
def runner():
    runner = CliRunner(mix_stderr=False)
    invoke = runner.invoke

    def _wrapped_invoke(*args, **kwargs):
        result = invoke(*args, **kwargs)
        # always write stderr on error so it shows up in captured test output
        if result.exit_code:
            sys.stderr.write(result.stderr)
        return result

    runner.invoke = _wrapped_invoke
    return runner


def test_job_list(runner):
    r = runner.invoke(cli, ["job", "list"])
    assert r.exit_code == 0


def test_lifecycle(runner, tmp_path):
    """
    Exercise job lifecycle

    1. submit
    2. list
    3. wait
    4. logs
    5. delete
    """

    test_sh = tmp_path / "test.sh"
    with test_sh.open("w") as f:
        f.write("set -ex; pwd; ls; env | sort\n")
    cmd = ["bash", "-c", "pwd; ls -l; ls -la * ; . test.sh"]
    cmd_json = json.dumps(cmd)
    # submit
    r = runner.invoke(
        cli,
        [
            "job",
            "submit",
            "--name=test",
            "--code",
            str(test_sh),
            "--command",
            cmd_json,
            "--image",
            "ubuntu:latest",
        ],
    )
    assert r.exit_code == 0
    job_name = r.output.strip()
    assert job_name.startswith("test-")

    # list
    r = runner.invoke(cli, ["job", "list"])
    assert r.exit_code == 0
    assert job_name in r.output

    # show
    r = runner.invoke(cli, ["job", "show", job_name])
    assert r.exit_code == 0
    assert job_name in r.output
    job = json.loads(r.output)
    assert job["metadata"]["name"] == job_name

    # list pods
    def _get_pod(job_name):
        r = runner.invoke(cli, ["pod", "list", "-o", "json", "--job-name", job_name])
        assert r.exit_code == 0
        pods = json.loads(r.stdout)["items"]
        return pods[0]

    pod = _get_pod(job_name)
    pod_name = pod["metadata"]["name"]
    while pod["status"]["phase"] in {"Pending", "Running"}:
        # wait for pod
        time.sleep(0.5)
        pod = _get_pod(job_name)

    # check pod list table
    r = runner.invoke(cli, ["pod", "list"])
    assert r.exit_code == 0
    assert pod_name in r.output

    # logs
    r = runner.invoke(cli, ["pod", "logs", pod_name])
    assert r.exit_code == 0
    assert "/code" in r.output
    assert "JUPYTER_IMAGE=ubuntu:latest" in r.output

    # delete job
    r = runner.invoke(cli, ["job", "delete", job_name])
    assert r.exit_code == 0

    # check job deleted
    # job delete can take a finite time,
    # so give it 30 seconds to finish
    r = runner.invoke(cli, ["job", "show", job_name])
    for i in range(6):
        # this also exercises error handling
        if r.exit_code:
            break
        else:
            time.sleep(5)
            r = runner.invoke(cli, ["job", "show", job_name])

    assert r.exit_code
    assert "not found" in r.output
    assert "Traceback" not in r.output

    # pods don't get deleted when jobs do, should they?
