import pytest

from django.core.exceptions import ValidationError
from django_kbatch_server.models import User, Job


@pytest.mark.django_db
def test_name_validates():
    user = User(username="me")
    user.save()
    job = Job(user=user, image="image", name="ABC")
    with pytest.raises(ValidationError, match="rfc"):
        job.clean_fields()
        job.save()
