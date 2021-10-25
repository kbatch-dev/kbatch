"""
Base settings to build other settings files upon.
"""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# planetary_computer/
APPS_DIR = BASE_DIR / "kbatch_server"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=True)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/


ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "localhost",
        "0.0.0.0",
        "127.0.0.1",
    ],
)

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    # "django_extensions",  # TODO: dev only
    "django_kbatch_server",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


ROOT_URLCONF = "kbatch_server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "kbatch_server.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
AUTH_USER_MODEL = "django_kbatch_server.User"
AUTHENTICATION_BACKENDS = [
    "django_kbatch_server.authentication.HubAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django Rest Framework

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "django_kbatch_server.authentication.RestFrameworkHubAuth",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

JUPYTERHUB_API_TOKEN = env("JUPYTERHUB_API_TOKEN", default=None)
JUPYTERHUB_SERVICE_PREFIX = env("JUPYTERHUB_SERVICE_PREFIX", default="")

KBATCH_JOB_NAMESPACE = env("KBATCH_JOB_NAMESPACE", default="default")
KBATCH_JOB_CPU_GUARANTEE = env("KBATCH_JOB_CPU_GUARANTEE", default=None)
KBATCH_JOB_CPU_LIMIT = env("KBATCH_JOB_CPU_LIMIT", default=None)
KBATCH_JOB_MEM_GUARANTEE = env("KBATCH_JOB_MEM_GUARANTEE", default=None)
KBATCH_JOB_MEM_LIMIT = env("KBATCH_JOB_MEM_LIMIT", default=None)
KBATCH_JOB_TOLERATIONS = env.list("KBATCH_JOB_TOLERATIONS", default=None)
KBATCH_JOB_LABELS = None
KBATCH_JOB_ANNOTATIONS = None
KBATCH_JOB_EXTRA_RESOURCE_LIMITS = None
KBATCH_JOB_EXTRA_RESOURCE_GUARANTEES = None

DEFAULT_FILE_STORAGE = env(
    "DEFAULT_FILE_STORAGE", default="django.core.files.storage.FileSystemStorage"
)
if DEFAULT_FILE_STORAGE == "storages.backends.azure_storage.AzureStorage":
    AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME", None)
    AZURE_CONTAINER = env("AZURE_CONTAINER", None)
    AZURE_SAS_TOKEN = env("AZURE_SAS_TOKEN")
