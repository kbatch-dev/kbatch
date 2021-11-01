from __future__ import annotations
import pytest
import kubernetes.client

import kbatch_proxy.utils
import kbatch_proxy.patch


@pytest.fixture
def k8s_job() -> kubernetes.client.V1Job:
    job = kubernetes.client.models.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=kubernetes.client.models.V1ObjectMeta(
            name="name",
            annotations={"foo": "bar"},
            labels={"baz": "qux"},
        ),
        spec=kubernetes.client.V1JobSpec(
            template=kubernetes.client.V1PodTemplateSpec(
                spec=kubernetes.client.V1PodSpec(
                    containers=[
                        kubernetes.client.V1Container(
                            args=["ls", "-lh"],
                            command=None,
                            image="alpine",
                            name="job",
                            env=[
                                kubernetes.client.V1EnvVar(
                                    name="MYENV", value="MYVALUE"
                                )
                            ],
                            resources=kubernetes.client.V1ResourceRequirements(),
                        )
                    ],
                    restart_policy="Never",
                    tolerations=None,
                ),
                metadata=kubernetes.client.V1ObjectMeta(
                    name="test-name-pod",
                    labels={"pod": "label"},
                    annotations={"pod": "annotations"},
                ),
            ),
            backoff_limit=4,
            ttl_seconds_after_finished=300,
        ),
    )
    return job


def test_parse_job(k8s_job: kubernetes.client.V1Job):
    result = kbatch_proxy.utils.parse(k8s_job.to_dict(), kubernetes.client.V1Job)
    assert result == k8s_job

    container = result.spec.template.spec.containers[0]
    assert isinstance(container, kubernetes.client.V1Container)
    assert container.args == ["ls", "-lh"]


def test_patch_job(k8s_job: kubernetes.client.V1Job):
    kbatch_proxy.patch.patch_job(k8s_job, annotations={}, labels={}, username="myuser")

    assert k8s_job.metadata.namespace == "myuser"
    assert k8s_job.spec.template.metadata.namespace == "myuser"
