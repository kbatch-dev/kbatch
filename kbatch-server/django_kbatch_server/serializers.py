import io
import zipfile

from rest_framework import serializers
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from django_kbatch_server.models import Job, Upload


class UploadDataField(serializers.JSONField):
    default_error_messages = {
        **dict(serializers.JSONField.default_error_messages),
        **{
            "incorrect": _(
                "Incorrect structure for upload data field. Must have a 'name' and 'content' field."
            )
        },
    }

    def to_internal_value(self, data):
        result = super().to_internal_value(data)

        if set(result) != {"name", "content"}:
            self.fail("incorrect")

        return result


class JobSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Job
        fields = [
            "url",
            "args",
            "command",
            "image",
            "name",
            "description",
            "env",
            "user",
            "upload",
            "upload_data",
        ]

    user = serializers.ReadOnlyField(source="user.username")

    # TODO: Might want to make this a JSON field with things like
    # content, name, content-type, ...
    upload_data = UploadDataField(allow_null=True, required=False, write_only=True)

    def create(self, validated_data):
        upload = validated_data.get("upload")
        upload_data = validated_data.pop("upload_data", None)

        if upload and upload_data:
            raise ValidationError("Cannot provide both 'upload', and 'upload_data'.")

        elif upload_data:
            name = upload_data["name"]
            content = upload_data["content"]
            sink = io.BytesIO()
            with zipfile.ZipFile(sink, mode="w") as zf:
                zf.writestr(name, content)

            sink.seek(0)
            assert zipfile.is_zipfile(sink)

            upload = Upload(
                user=validated_data["user"],
                file=SimpleUploadedFile(
                    "upload.zip", sink.getvalue(), content_type="application/zip"
                ),
            )
            upload.save()

            validated_data["upload"] = upload

        result = super().create(validated_data)
        return result


class ZipFileField(serializers.FileField):
    default_error_messages = {
        **dict(serializers.FileField.default_error_messages),
        **{"zip": _("The submitted file must be a ZIP archive.")},
    }

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if not zipfile.is_zipfile(data.file):
            self.fail("zip")
        return data


class UploadSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Upload
        fields = ["url", "file", "user"]

    file = ZipFileField(write_only=True)
    user = serializers.ReadOnlyField(source="user.username")
