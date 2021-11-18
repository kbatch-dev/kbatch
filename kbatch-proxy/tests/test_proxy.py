import pathlib

import pytest
import kubernetes.client
import yaml

import kbatch_proxy.utils
import kbatch_proxy.main
import kbatch_proxy.patch


HERE = pathlib.Path(__file__).parent


@pytest.fixture
def k8s_job() -> kubernetes.client.V1Job:
    job = kubernetes.client.models.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=kubernetes.client.models.V1ObjectMeta(
            name="name",
            generate_name="name-",
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
    kbatch_proxy.patch.patch(
        k8s_job, None, annotations={}, labels={}, username="myuser"
    )

    assert k8s_job.metadata.namespace == "myuser"
    assert k8s_job.spec.template.metadata.namespace == "myuser"


@pytest.mark.parametrize(
    "username, expected",
    [
        ("test", "test"),
        ("TEST", "test"),
        ("test123test", "test123test"),
        ("test-test", "test-test"),
        ("taugspurger@microsoft.com", "taugspurger-microsoft-com"),
    ],
)
def test_namespace_for_username(username, expected):
    result = kbatch_proxy.patch.namespace_for_username(username)
    assert result == expected

    result = kbatch_proxy.main.User(name=username, groups=[]).namespace
    assert result == expected


def test_namespace_configmap():
    cm = kubernetes.client.V1ConfigMap(metadata=kubernetes.client.V1ObjectMeta())
    assert cm.metadata.namespace is None
    kbatch_proxy.patch.add_namespace_configmap(cm, "my-namespace")
    assert cm.metadata.namespace == "my-namespace"


@pytest.mark.parametrize("has_init_containers", [True, False])
@pytest.mark.parametrize("has_volumes", [True, False])
def test_add_unzip_init_container(
    k8s_job: kubernetes.client.V1Job, has_init_containers: bool, has_volumes: bool
):
    if has_init_containers:
        k8s_job.spec.template.spec.init_containers = [
            kubernetes.client.V1Container(name="present-container")
        ]

    if has_volumes:
        k8s_job.spec.template.spec.volumes = [
            kubernetes.client.V1Volume(name="present-volume", empty_dir={})
        ]
        k8s_job.spec.template.spec.containers[0].volume_mounts = [
            kubernetes.client.V1VolumeMount(
                name="present-volume", mount_path="/present-volume"
            )
        ]

    kbatch_proxy.patch.add_unzip_init_container(k8s_job)

    n_init_containers = int(has_init_containers) + 1
    assert len(k8s_job.spec.template.spec.init_containers) == n_init_containers

    n_volumes = int(has_volumes) + 2
    assert len(k8s_job.spec.template.spec.volumes) == n_volumes

    n_volume_mounts = int(has_volumes) + 1
    assert (
        len(k8s_job.spec.template.spec.containers[0].volume_mounts) == n_volume_mounts
    )

    # now patch with the actual name
    config_map = kubernetes.client.V1ConfigMap(
        metadata=kubernetes.client.V1ObjectMeta(
            name="actual-name", namespace="my-namespace"
        )
    )
    kbatch_proxy.patch.add_submitted_configmap_name(k8s_job, config_map)
    assert k8s_job.spec.template.spec.volumes[-2].config_map.name == "actual-name"


@pytest.mark.parametrize(
    "job_env", [None, [], [kubernetes.client.V1EnvVar(name="SAS_TOKEN", value="TOKEN")]]
)
def test_extra_env(job_env, k8s_job: kubernetes.client.V1Job):
    has_env = bool(job_env)
    k8s_job.spec.template.spec.containers[0].env = job_env

    extra_env = {"MY_ENV": "VALUE"}
    kbatch_proxy.patch.add_extra_env(k8s_job, extra_env, api_token="super-secret")

    if has_env:
        expected = [
            kubernetes.client.V1EnvVar(name="SAS_TOKEN", value="TOKEN"),
            kubernetes.client.V1EnvVar(name="MY_ENV", value="VALUE"),
            kubernetes.client.V1EnvVar(name="JUPYTER_IMAGE", value="alpine"),
            kubernetes.client.V1EnvVar(name="JUPYTER_IMAGE_SPEC", value="alpine"),
            kubernetes.client.V1EnvVar(
                name="JUPYTERHUB_API_TOKEN", value="super-secret"
            ),
        ]
    else:
        expected = [
            kubernetes.client.V1EnvVar(name="MY_ENV", value="VALUE"),
            kubernetes.client.V1EnvVar(name="JUPYTER_IMAGE", value="alpine"),
            kubernetes.client.V1EnvVar(name="JUPYTER_IMAGE_SPEC", value="alpine"),
            kubernetes.client.V1EnvVar(
                name="JUPYTERHUB_API_TOKEN", value="super-secret"
            ),
        ]

    assert k8s_job.spec.template.spec.containers[0].env == expected


def test_set_job_ttl_seconds_after_finished(k8s_job: kubernetes.client.V1Job):
    kbatch_proxy.patch.patch(
        k8s_job, None, username="foo", ttl_seconds_after_finished=10
    )
    assert k8s_job.spec.ttl_seconds_after_finished == 10


def test_add_node_affinity(k8s_job: kubernetes.client.V1Job):
    job_template = yaml.safe_load((HERE / "job_template.yaml").read_text())
    job_template = kbatch_proxy.utils.parse(
        job_template, kubernetes.client.V1Job
    ).to_dict()

    job_data = k8s_job.to_dict()

    result = kbatch_proxy.utils.merge_json_objects(job_data, job_template)
    result = kbatch_proxy.utils.parse(result, kubernetes.client.V1Job)

    node_affinity = result.spec.template.spec.affinity.node_affinity
    terms = node_affinity.required_during_scheduling_ignored_during_execution.node_selector_terms[
        0
    ].match_expressions[
        0
    ]
    assert terms.key == "hub.jupyter.org/node-purpose"
    assert terms.operator == "In"
    assert terms.values == ["user"]
    assert job_data["spec"]["backoff_limit"] == 4  # overridden by template
    assert result.spec.backoff_limit == 0  # overridden by template
