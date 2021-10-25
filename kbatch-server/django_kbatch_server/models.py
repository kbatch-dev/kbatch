import logging
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from . import backend
from . import types_


logger = logging.getLogger(__name__)


class User(AbstractUser):
    pass


name_validator = RegexValidator(
    # TODO: this xpr was taken from the k8s error, but doesn't seem to validate correctly.
    # e.g. ABC-123 passes, but fails at k8s.
    regex=r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
    message=(
        "The 'name' field must be a valid RFC 1123 subdomain. See "
        "https://datatracker.ietf.org/doc/html/rfc1123/."
    ),
)


class Upload(models.Model):
    # TODO: Verify if we need additional validation that the file is a Zip
    # here and in fields, not just serailizers.
    file = models.FileField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class Job(models.Model):
    args = models.JSONField(blank=True, null=True)
    command = models.JSONField(
        blank=True, null=True
    )  # TODO: validate that this is a list
    image = models.TextField(default="alpine")
    name = models.TextField(validators=[name_validator])
    env = models.JSONField(blank=True, null=True)

    # Relations
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # this could maybe be a many to many?
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk:
            # We're updating an existing record.
            return super().save(*args, **kwargs)

        result = super().save(*args, **kwargs)

        job = types_.Job.from_model(self)
        k8s_config = types_.KubernetesConfig.from_settings()

        k8s_job = backend.make_job(job=job, k8s_config=k8s_config)
        logger.info("Submitting configmap for job %d", self.pk)

        batch_api = backend.make_api()

        logger.info("Submitting job %d", self.pk)
        resp = backend.submit_job(batch_api, k8s_job)  # TODO: async
        logger.debug("resp %s", resp)

        return result
