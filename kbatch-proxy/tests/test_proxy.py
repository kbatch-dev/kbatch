import pathlib

import pytest
import kubernetes.client
import yaml

import kbatch_proxy.utils
import kbatch_proxy.main
import kbatch_proxy.patch


HERE = pathlib.Path(__file__).parent


def k8s_job_spec() -> kubernetes.client.V1JobSpec:
    return kubernetes.client.V1JobSpec(
        template=kubernetes.client.V1PodTemplateSpec(
            spec=kubernetes.client.V1PodSpec(
                containers=[
                    kubernetes.client.V1Container(
                        args=["ls", "-lh"],
                        command=None,
                        image="alpine",
                        name="job",
                        env=[kubernetes.client.V1EnvVar(name="MYENV", value="MYVALUE")],
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
    )


def k8s_job() -> kubernetes.client.V1Job:
    metadata = kubernetes.client.V1ObjectMeta(
        name="name",
        generate_name="name-",
        annotations={"foo": "bar"},
        labels={"baz": "qux"},
    )
    return kubernetes.client.models.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=metadata,
        spec=k8s_job_spec(),
    )


def k8s_cronjob() -> kubernetes.client.V1CronJob:
    metadata = kubernetes.client.V1ObjectMeta(
        name="name-cron",
        generate_name="name-cron-",
        annotations={"foo": "bar"},
        labels={"baz": "qux"},
    )
    return kubernetes.client.V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=metadata,
        spec=kubernetes.client.V1CronJobSpec(
            schedule="*/5 * * * *",
            job_template=kubernetes.client.V1JobTemplateSpec(
                spec=k8s_job_spec(),
                metadata=metadata,
            ),
        ),
    )


@pytest.fixture(scope="function", params=[k8s_job, k8s_cronjob])
def job(request):
    j = request.param()
    if isinstance(j, kubernetes.client.V1CronJob):
        j = j.spec.job_template

    yield j


def test_parse_job(job):
    if isinstance(job, kubernetes.client.V1Job):
        result = kbatch_proxy.utils.parse(job.to_dict(), kubernetes.client.V1Job)
    else:
        result = kbatch_proxy.utils.parse(
            job.to_dict(), kubernetes.client.V1JobTemplateSpec
        )

    container = result.spec.template.spec.containers[0]
    assert isinstance(container, kubernetes.client.V1Container)
    assert container.args == ["ls", "-lh"]


def test_patch_job(job):
    kbatch_proxy.patch.patch(job, None, annotations={}, labels={}, username="myuser")

    assert job.metadata.namespace == "myuser"
    assert job.spec.template.metadata.namespace == "myuser"


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
def test_add_unzip_init_container(job, has_init_containers: bool, has_volumes: bool):
    if has_init_containers:
        job.spec.template.spec.init_containers = [
            kubernetes.client.V1Container(name="present-container")
        ]

    if has_volumes:
        job.spec.template.spec.volumes = [
            kubernetes.client.V1Volume(name="present-volume", empty_dir={})
        ]
        job.spec.template.spec.containers[0].volume_mounts = [
            kubernetes.client.V1VolumeMount(
                name="present-volume", mount_path="/present-volume"
            )
        ]

    kbatch_proxy.patch.add_unzip_init_container(job)

    n_init_containers = int(has_init_containers) + 1
    assert len(job.spec.template.spec.init_containers) == n_init_containers

    n_volumes = int(has_volumes) + 2
    assert len(job.spec.template.spec.volumes) == n_volumes

    n_volume_mounts = int(has_volumes) + 1
    assert len(job.spec.template.spec.containers[0].volume_mounts) == n_volume_mounts

    # now patch with the actual name
    config_map = kubernetes.client.V1ConfigMap(
        metadata=kubernetes.client.V1ObjectMeta(
            name="actual-name", namespace="my-namespace"
        )
    )
    kbatch_proxy.patch.add_submitted_configmap_name(job, config_map)
    assert job.spec.template.spec.volumes[-2].config_map.name == "actual-name"


@pytest.mark.parametrize(
    "job_env", [None, [], [kubernetes.client.V1EnvVar(name="SAS_TOKEN", value="TOKEN")]]
)
def test_extra_env(job, job_env):
    has_env = bool(job_env)

    # make copy to avoid mutation
    job.spec.template.spec.containers[0].env = (
        job_env.copy() if job_env is not None else None
    )

    extra_env = {"MY_ENV": "VALUE"}
    kbatch_proxy.patch.add_extra_env(job, extra_env, api_token="super-secret")

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

    assert job.spec.template.spec.containers[0].env == expected


def test_set_job_ttl_seconds_after_finished(job):
    kbatch_proxy.patch.patch(job, None, username="foo", ttl_seconds_after_finished=10)
    assert job.spec.ttl_seconds_after_finished == 10


def test_add_node_affinity(job):
    job_template = yaml.safe_load((HERE / "job_template.yaml").read_text())
    job_template = kbatch_proxy.utils.parse(
        job_template, kubernetes.client.V1Job
    ).to_dict()

    job_data = job.to_dict()

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
