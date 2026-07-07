"""Development settings."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# Convenient for local access from other devices on the LAN.
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=["*"])

INTERNAL_IPS = ["127.0.0.1"]

# Send password-reset and order emails to the console in dev.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
