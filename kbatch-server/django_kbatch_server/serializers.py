from rest_framework import serializers
from django.contrib.auth.models import Group
from django_kbatch_server.models import User, Job


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class JobSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Job
        fields = ["url", "command", "script", "image", "name", "env", "user"]

    user = serializers.ReadOnlyField(source="user.username")
