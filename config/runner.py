from django.test.runner import DiscoverRunner

# Our apps live under apps/ and are imported with short labels (apps/ is on
# sys.path). unittest's default discovery starts at the repo root and won't
# descend into the non-package apps/ dir, so a bare `manage.py test` would find
# nothing. Defaulting to the app labels makes discovery work via the app
# registry (each app's own tests.py), with no double-import.
LOCAL_APP_LABELS = [
    "core",
    "accounts",
    "products",
    "cart",
    "orders",
    "wholesale",
    "content",
    "notifications",
]


class NLKTestRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, **kwargs):
        if not test_labels:
            test_labels = LOCAL_APP_LABELS
        return super().build_suite(test_labels, **kwargs)
