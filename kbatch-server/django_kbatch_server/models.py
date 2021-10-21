import logging
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings


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


class Job(models.Model):
    command = models.JSONField(
        blank=True, null=True
    )  # TODO: validate that this is a list
    script = models.TextField(blank=True, null=True)
    image = models.TextField()
    name = models.TextField(validators=[name_validator])
    env = models.JSONField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        from . import backend

        if self.pk:
            # We're updating an existing record.
            return super().save(*args, **kwargs)

        result = super().save(*args, **kwargs)
        k8s_job, config_map = backend.make_job(
            job=self,
            env=self.env,  # TODO remove
            namespace=settings.KBATCH_JOB_NAMESPACE,
            cpu_guarantee=settings.KBATCH_JOB_CPU_GUARANTEE,
            cpu_limit=settings.KBATCH_JOB_CPU_LIMIT,
            mem_guarantee=settings.KBATCH_JOB_MEM_GUARANTEE,
            mem_limit=settings.KBATCH_JOB_MEM_LIMIT,
            tolerations=settings.KBATCH_JOB_TOLERATIONS,
        )
        logger.info("Submitting configmap for job %d", self.pk)

        api, batch_api = backend.make_api()

        resp = backend.submit_configmap(api, config_map)  # TODO: async

        logger.debug("resp %s", resp)

        logger.info("Submitting job %d", self.pk)
        resp = backend.submit_job(batch_api, k8s_job)  # TODO: async
        logger.debug("resp %s", resp)

        return result
