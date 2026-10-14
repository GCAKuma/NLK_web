"""Production settings. Runs Gunicorn behind Nginx (TLS terminated at Nginx)."""
from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env
from django.core.exceptions import ImproperlyConfigured

DEBUG = False
RUNTIME_DATABASE_ROLE = env("RUNTIME_DATABASE_ROLE", default="nlk_app")
AWS_BACKUP_BUCKET_NAME = env("AWS_BACKUP_BUCKET_NAME", default="")
SECRET_KEY = env("SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("insecure", "CHANGE", "django-insecure")):
    raise ImproperlyConfigured("Set a strong production SECRET_KEY of at least 50 characters.")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set explicit production ALLOWED_HOSTS.")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# WhiteNoise as a fallback static server (Nginx serves /static/ in front of it).
MIDDLEWARE = MIDDLEWARE[:1] + [
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + MIDDLEWARE[1:]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "private": {"BACKEND": "core.storage.PrivateFileSystemStorage"},
}

DATABASES["default"] = env.db("DATABASE_URL")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires PostgreSQL.")
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"].setdefault("OPTIONS", {}).setdefault("connect_timeout", 10)
DATABASES["default"]["OPTIONS"].setdefault("sslmode", "require")
CACHES["default"]["OPTIONS"] = {"socket_connect_timeout": 3, "socket_timeout": 3}
if DATABASES["default"]["OPTIONS"]["sslmode"] not in {"require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured("Production database connections must use TLS.")

# ---------------------------------------------------------------------------
# Security (Nginx terminates TLS and forwards X-Forwarded-Proto)
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^health/live/$", r"^health/ready/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = False

# Cap request bodies (bank slip / invoice uploads).
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Optional object storage — S3 / Cloudflare R2 / DO Spaces (django-storages).
# Toggle with USE_S3=True and provide credentials; otherwise media stays on disk.
# ---------------------------------------------------------------------------
if env.bool("USE_S3", default=False):
    # Boto3 uses the EC2 instance role. No permanent access keys are needed.
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)  # R2/Spaces
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600
    AWS_DEFAULT_ACL = None
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    STORAGES["private"] = {"BACKEND": "core.s3_storage.PrivateS3Storage"}

# ---------------------------------------------------------------------------
# Error monitoring — set SENTRY_DSN to enable (free tier is fine to start).
# Leaving it blank keeps Sentry fully inert; no code path depends on it.
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            LoggingIntegration(level=None, event_level="ERROR"),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,  # don't ship customer emails/addresses to Sentry
    )

# ---------------------------------------------------------------------------
# Logging — everything to stdout for the container runtime to collect.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}
