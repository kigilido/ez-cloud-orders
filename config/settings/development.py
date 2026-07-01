from .base import *  # noqa: F403

DEBUG = env("DEBUG", default=True)  # noqa: F405

ALLOWED_HOSTS = list(
    dict.fromkeys(ALLOWED_HOSTS + ["192.168.50.27", "47.17.125.155"])  # noqa: F405
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
