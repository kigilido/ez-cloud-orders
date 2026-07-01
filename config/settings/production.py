from .base import *  # noqa: F403

DEBUG = env("DEBUG", default=False)  # noqa: F405

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])  # noqa: F405

if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
