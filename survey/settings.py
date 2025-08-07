import os
from pathlib import Path

from django.conf import settings

# https://djecrety.ir/
SECRET_KEY = "7&yd=z5z7tvh@st0c78ia0-5kb%2u@ic72x*#e*31#6egc_!@e"

ROOT = os.path.dirname(os.path.abspath(__file__))
USER_DID_NOT_ANSWER = getattr(settings, "USER_DID_NOT_ANSWER", "Left blank")
TEX_CONFIGURATION_FILE = getattr(settings, "TEX_CONFIGURATION_FILE", Path(ROOT, "doc", "example_conf.yaml"))
SURVEY_DEFAULT_PIE_COLOR = getattr(settings, "SURVEY_DEFAULT_PIE_COLOR", "red!50")
CHOICES_SEPARATOR = getattr(settings, "CHOICES_SEPARATOR", ",")
EXCEL_COMPATIBLE_CSV = False
DEFAULT_SURVEY_PUBLISHING_DURATION = 7


DEBUG_ADMIN_NAME = "test_admin"
DEBUG_ADMIN_PASSWORD = "test_password"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

MEDIA_URL = "/media/"
STATIC_URL = "/static/"

MEDIA_ROOT = Path(ROOT, "media")
STATIC_ROOT = Path(ROOT, "static")

STATICFILES_DIRS = []

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(ROOT, "survey", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "survey.test_urls"
WSGI_APPLICATION = "survey.wsgi.application"

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django_pluralize_ru",
    "crispy_forms",
    "crispy_bootstrap5",
    "survey",
)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

SITE_ID = 1
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = (Path(ROOT, "locale"),)
LANGUAGE_CODE = "en"
LANGUAGES = (
    ("en", "english"),
    ("ru", "russian"),
)

# Crispy Forms настройки
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = ("bootstrap5",)
