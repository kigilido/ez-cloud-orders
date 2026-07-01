from .base import *  # noqa: F403

DEBUG = env("DEBUG", default=True)  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.50.27", "47.17.125.155"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
