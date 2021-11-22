from kbatch._backend import make_job
from kbatch._types import Job


def test_profile_image():
    job = Job(name="test")
    profile = dict(image="alpine")
    result = make_job(job, profile=profile)
    assert result.spec.template.spec.containers[0].image == "alpine"


def test_job_image_overrides_profile_image():
    job = Job(name="test", image="alpine")
    profile = dict(image="not-alpine")
    result = make_job(job, profile=profile)
    assert result.spec.template.spec.containers[0].image == "alpine"


def test_profile_sets_resources():
    job = Job(name="test", image="alpine")
    profile = dict(
        resources=dict(
            requests={"cpu": "0.5", "memory": "0.5Gi", "nvidia.com/gpu": "1"},
            limits=dict(cpu="1", memory="1Gi"),
        )
    )
    result = make_job(job, profile=profile)
    assert result.spec.template.spec.containers[0].resources.requests == {
        "cpu": "0.5",
        "memory": "0.5Gi",
        "nvidia.com/gpu": "1",
    }

    assert result.spec.template.spec.containers[0].resources.limits == {
        "cpu": "1",
        "memory": "1Gi",
    }


def test_profile_sets_tolerations():
    job = Job(name="test", image="alpine")
    profile = dict(
        tolerations=[
            dict(
                key="nvidia.com/gpu",
                operator="Equal",
                value="present",
                effect="NoSchedule",
            ),
            dict(
                key="hub.jupyter.org_dedicated",
                operator="Equal",
                value="user",
                effect="NoSchedule",
            ),
        ]
    )
    result = make_job(job, profile)
    assert len(result.spec.template.spec.tolerations) == 2
    for a, b in zip(result.spec.template.spec.tolerations, profile["tolerations"]):
        a2 = a.to_dict()
        a2.pop("toleration_seconds")
        assert a2 == b
