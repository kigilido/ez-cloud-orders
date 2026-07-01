from pathlib import Path

import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    EMAIL_PORT=(int, 587),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

_DEFAULT_ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "ez-cloud-orders-production.up.railway.app",
]

# Comma-separated list in ALLOWED_HOSTS env var, e.g.:
# ALLOWED_HOSTS=example.com,.railway.app
ALLOWED_HOSTS: list[str] = list(
    dict.fromkeys(_DEFAULT_ALLOWED_HOSTS + env.list("ALLOWED_HOSTS", default=[]))
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.customers",
    "apps.orders",
    "apps.connectors",
    "apps.billing",
    "apps.dashboard",
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

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://user:pass@localhost:5432/ez_cloud_orders",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Celery
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True

# External integrations (configured via env — do not hard-code)
ZOHO_CLIENT_ID = env("ZOHO_CLIENT_ID", default="")
ZOHO_CLIENT_SECRET = env("ZOHO_CLIENT_SECRET", default="")
ZOHO_REFRESH_TOKEN = env("ZOHO_REFRESH_TOKEN", default="")
ZOHO_ORG_ID = env("ZOHO_ORG_ID", default="")

AZURE_TENANT_ID = env("AZURE_TENANT_ID", default="")
AZURE_CLIENT_ID = env("AZURE_CLIENT_ID", default="")
AZURE_CLIENT_SECRET = env("AZURE_CLIENT_SECRET", default="")
SHAREPOINT_SITE_ID = env("SHAREPOINT_SITE_ID", default="")
SHAREPOINT_FOLDER_ID = env("SHAREPOINT_FOLDER_ID", default="")

GOOGLE_SERVICE_ACCOUNT_JSON = env("GOOGLE_SERVICE_ACCOUNT_JSON", default="")

SHAREPOINT_REPORT_EMAIL = env("SHAREPOINT_REPORT_EMAIL", default="")
GOOGLE_DRIVE_REPORT_EMAIL = env("GOOGLE_DRIVE_REPORT_EMAIL", default="")

BILLING_DAY = env("BILLING_DAY", default="last")
