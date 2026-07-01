from .base import *  # noqa: F403

DEBUG = env("DEBUG", default=False)  # noqa: F405

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
CSRF_TRUSTED_ORIGINS = ["https://ez-cloud-orders-production.up.railway.app"]
CSRF_TRUSTED_ORIGINS = ["http://ez-cloud-orders-production.up.railway.app"]
