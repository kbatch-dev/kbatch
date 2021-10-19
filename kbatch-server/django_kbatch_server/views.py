from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework import permissions
from django_kbatch_server.serializers import (
    UserSerializer,
    GroupSerializer,
    JobSerializer,
)
from django_kbatch_server.models import User, Job


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().order_by("id")
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Job.objects.filter(user=user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
