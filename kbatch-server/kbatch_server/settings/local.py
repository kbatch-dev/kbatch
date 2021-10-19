from .base import *  # noqa
from .base import env

SECRET_KEY = "django-insecure-8mv!9buzgip^c-t26wo(3ud9lq$(%c)e9m%xg+2*dndcc5l#=a"
JUPYTERHUB_API_TOKEN = env("JUPYTERHUB_API_TOKEN", default="super-secret")
DEBUG = True
