# dotori_core/settings.py
from pathlib import Path
import os
import importlib
import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    USE_SQLITE=(bool, True),               
    USE_INMEMORY_CHANNELS=(bool, True),    
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

#
# 핵심 설정
#
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret")
DEBUG = env("DJANGO_DEBUG")


ALLOWED_HOSTS = [
    "54.180.149.45",
    "127.0.0.1",
    "localhost",
]


INSTALLED_APPS = [
    "daphne",  # ASGI 서버
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "channels",

    # local apps
    "apps.dotori_accounts",
    "apps.dotori_documents",
    "apps.dotori_summaries",
    "apps.dotori_common",
    "apps.dotori_detector"
    "apps.dotori_roleplay",
    "apps.dotori_memberships",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",       
    "dotori_core.middleware.AllowCORSForMedia",    
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dotori_core.urls"
ASGI_APPLICATION = "dotori_core.asgi.application"

try:
    importlib.import_module("dotori_core.wsgi")
    WSGI_APPLICATION = "dotori_core.wsgi.application"
except ModuleNotFoundError:
    WSGI_APPLICATION = None 

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  
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


if env("USE_SQLITE"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default="dotori"),
            "USER": env("POSTGRES_USER", default="dotori"),
            "PASSWORD": env("POSTGRES_PASSWORD", default="dotori"),
            "HOST": env("POSTGRES_HOST", default="localhost"),
            "PORT": env("POSTGRES_PORT", default="5432"),
        }
    }


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}


CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ORIGINS", default=[])
CORS_ALLOW_ALL_ORIGINS = True if not CORS_ALLOWED_ORIGINS else False

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


if env("USE_INMEMORY_CHANNELS"):
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [env("REDIS_URL", default="redis://localhost:6379/0")],
            },
        }
    }

CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = False


COOLSMS_API_KEY = env("COOLSMS_API_KEY", default="")
COOLSMS_API_SECRET = env("COOLSMS_API_SECRET", default="")
COOLSMS_SENDER_NUMBER = env("COOLSMS_SENDER_NUMBER", default="")
