"""Environment-based settings for local development."""

import os
import re
from decimal import Decimal, DecimalException
from math import isfinite
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DEBUG", os.getenv("DJANGO_DEBUG", "False")).strip().lower() in {
    "true",
    "1",
    "yes",
}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]"),
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "inventory.apps.InventoryConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # DB_* takes precedence; retain support for existing POSTGRES_* files.
        "NAME": os.getenv("DB_NAME") or os.environ["POSTGRES_DB"],
        "USER": os.getenv("DB_USER") or os.environ["POSTGRES_USER"],
        "PASSWORD": os.getenv("DB_PASSWORD") or os.environ["POSTGRES_PASSWORD"],
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Use DRF's centralized exception handling until domain exceptions are defined.
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

EXCHANGE_RATE_API_URL = os.getenv("EXCHANGE_RATE_API_URL", "").strip() or (
    "https://api.exchangerate-api.com/v4/latest/USD"
)
LOCAL_CURRENCY = (os.getenv("LOCAL_CURRENCY") or "EUR").strip().upper()
if not re.fullmatch(r"[A-Z]{3}", LOCAL_CURRENCY):
    raise ImproperlyConfigured("LOCAL_CURRENCY must be a three-letter currency code.")
default_rate = os.getenv("EXCHANGE_RATE_DEFAULT_RATE") or {"EUR": "0.85", "USD": "1"}.get(LOCAL_CURRENCY)
if default_rate is None:
    raise ImproperlyConfigured("Set EXCHANGE_RATE_DEFAULT_RATE for the configured LOCAL_CURRENCY.")
try:
    EXCHANGE_RATE_DEFAULT_RATE = Decimal(default_rate)
except DecimalException as error:
    raise ImproperlyConfigured("EXCHANGE_RATE_DEFAULT_RATE must be a positive finite number.") from error
if not EXCHANGE_RATE_DEFAULT_RATE.is_finite() or EXCHANGE_RATE_DEFAULT_RATE <= 0:
    raise ImproperlyConfigured("EXCHANGE_RATE_DEFAULT_RATE must be a positive finite number.")
try:
    EXCHANGE_RATE_API_TIMEOUT = float(os.getenv("EXCHANGE_RATE_API_TIMEOUT") or "10")
    EXCHANGE_RATE_CACHE_TTL = int(os.getenv("EXCHANGE_RATE_CACHE_TTL") or "3600")
    EXCHANGE_RATE_FALLBACK_TTL = int(os.getenv("EXCHANGE_RATE_FALLBACK_TTL") or "86400")
except ValueError as error:
    raise ImproperlyConfigured("Exchange-rate timeout and cache durations must be numeric.") from error
if (
    not isfinite(EXCHANGE_RATE_API_TIMEOUT)
    or EXCHANGE_RATE_API_TIMEOUT <= 0
    or EXCHANGE_RATE_CACHE_TTL <= 0
    or EXCHANGE_RATE_FALLBACK_TTL < EXCHANGE_RATE_CACHE_TTL
):
    raise ImproperlyConfigured(
        "Exchange-rate timeout and cache durations must be positive; "
        "fallback duration must be at least the fresh-cache duration."
    )

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
