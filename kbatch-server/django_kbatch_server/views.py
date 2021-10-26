from rest_framework import viewsets
from rest_framework import permissions
from django_kbatch_server.serializers import (
    JobSerializer,
    UploadSerializer,
)
from django_kbatch_server.models import Job, Upload
from rest_framework.parsers import MultiPartParser, FormParser


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().order_by("id")
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Job.objects.filter(user=user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UploadViewSet(viewsets.ModelViewSet):
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    queryset = Upload.objects.all().order_by("id")
    serializer_class = UploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Upload.objects.filter(user=user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
