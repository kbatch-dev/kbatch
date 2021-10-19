"""

"""
# TODO: Split to a standalone app
from django.conf import settings
from django.contrib.auth import get_user_model

from django.contrib.auth.backends import BaseBackend
from django.utils.translation import gettext_lazy as _
from jupyterhub.services.auth import HubAuth
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions

api_token = settings.JUPYTERHUB_API_TOKEN

auth = HubAuth(
    api_token=api_token,
    cache_max_age=60,  # TODO: configurable setting
)
User = get_user_model()


class HubAuthBackend(BaseBackend):
    """ """

    def authenticate(self, request, token=None):
        # Check the username/password and return a user.
        cookie = request.cookies.get(auth.cookie_name)
        token = request.headers.get(auth.auth_header_name)

        if cookie:
            user = auth.user_for_cookie(cookie)
        elif token:
            user = auth.user_for_token(token)
        else:
            user = None
        if user:
            return user
        else:
            return None


class RestFrameworkHubAuth(TokenAuthentication):
    def authenticate_credentials(self, key):
        user_data = auth.user_for_token(key)
        if user_data:
            user, created = User.objects.get_or_create(
                username=user_data["name"],
                # TODO: groups
                # TODO: admin?
            )
            if not user.is_active:
                raise exceptions.AuthenticationFailed(_("User inactive or deleted."))
            return (user, key)
        else:
            raise exceptions.AuthenticationFailed(_("Invalid token."))
