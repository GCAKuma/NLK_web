"""AppConfig that installs our dashboard-enabled admin site as the default.

Kept in its own module (not core/apps.py) so it doesn't clash with CoreConfig
when Django auto-detects the default app config for the `core` app.
"""
from django.contrib.admin.apps import AdminConfig


class NLKAdminConfig(AdminConfig):
    default_site = "core.admin_site.NLKAdminSite"
