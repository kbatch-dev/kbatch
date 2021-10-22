import pytest
import kubernetes.client

from django_kbatch_server import types_
from django_kbatch_server import backend


@pytest.fixture
def model_user():
    return types_.User(username="taugspurger")


@pytest.fixture
def model_job(model_user):
    return types_.Job(
        id=1, name="name", command=["ls", "-lh"], image="alpine", user=model_user
    )


def test_resource_limits(model_job):
    k8s_config = types_.KubernetesConfig(
        cpu_guarantee="100m",
        cpu_limit="500m",
        mem_guarantee="1Gi",
        mem_limit="2Gi",
        extra_resource_guarantees={"nvidia.com/gpu": 1},
        extra_resource_limits={"nvidia.com/gpu": 1},
    )

    job = backend.make_job(model_job, k8s_config)

    container = job.spec.template.spec.containers[0]

    assert container.resources.requests["cpu"] == "100m"
    assert container.resources.limits["cpu"] == "500m"

    assert container.resources.requests["memory"] == "1Gi"
    assert container.resources.limits["memory"] == "2Gi"

    assert container.resources.requests["nvidia.com/gpu"] == 1
    assert container.resources.limits["nvidia.com/gpu"] == 1


@pytest.mark.parametrize(
    "env",
    [
        {"KEY1": "VALUE1", "KEY2": "VALUE2"},
        [
            kubernetes.client.V1EnvVar(name="KEY1", value="VALUE1"),
            kubernetes.client.V1EnvVar(name="KEY2", value="VALUE2"),
        ],
    ],
)
def test_env(model_user, env):
    k8s_config = types_.KubernetesConfig()
    jobin = types_.Job(
        id=1, name="name", command=["ls -lh"], image="alpine", user=model_user, env=env
    )

    job = backend.make_job(jobin, k8s_config)
    container = job.spec.template.spec.containers[0]
    assert container.env == [
        kubernetes.client.V1EnvVar(name="KEY1", value="VALUE1"),
        kubernetes.client.V1EnvVar(name="KEY2", value="VALUE2"),
    ]


@pytest.mark.parametrize(
    "toleration",
    [
        kubernetes.client.V1Toleration(
            key="hub.jupyter.org/dedicated", value="user", effect="NoSchedule"
        ),
        "hub.jupyter.org/dedicated=user:NoSchedule",
    ],
)
def test_node_tolerations(model_job, toleration):
    k8s_config = types_.KubernetesConfig(tolerations=[toleration])
    job = backend.make_job(model_job, k8s_config)
    pod = job.spec.template.spec

    assert pod.tolerations == [
        kubernetes.client.V1Toleration(
            key="hub.jupyter.org/dedicated", value="user", effect="NoSchedule"
        )
    ]
