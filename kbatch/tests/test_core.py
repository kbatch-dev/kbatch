import io
import pathlib
import zipfile
import pytest
import kubernetes

import kbatch


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
    # k8s_config = types_.KubernetesConfig()
    jobin = kbatch.Job(name="name", command=["ls -lh"], image="alpine", env=env)

    job = kbatch.make_job(jobin)
    container = job.spec.template.spec.containers[0]
    assert container.env == [
        kubernetes.client.V1EnvVar(name="KEY1", value="VALUE1"),
        kubernetes.client.V1EnvVar(name="KEY2", value="VALUE2"),
    ]


# @pytest.mark.parametrize(
#     "toleration",
#     [
#         kubernetes.client.V1Toleration(
#             key="hub.jupyter.org/dedicated", value="user", effect="NoSchedule"
#         ),
#         "hub.jupyter.org/dedicated=user:NoSchedule",
#     ],
# )
# def test_node_tolerations(model_job, toleration):
#     # k8s_config = types_.KubernetesConfig(tolerations=[toleration])
#     job = kbatch.make_job(model_job, k8s_config)
#     pod = job.spec.template.spec

#     assert pod.tolerations == [
#         kubernetes.client.V1Toleration(
#             key="hub.jupyter.org/dedicated", value="user", effect="NoSchedule"
#         )
#     ]


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
