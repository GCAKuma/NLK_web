from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from notifications.models import NotificationJob


class Command(BaseCommand):
    help = "Exit nonzero when notification delivery needs attention; suitable for a monitor."

    def handle(self, *args, **options):
        pending = NotificationJob.objects.filter(completed_at__isnull=True)
        failed = pending.filter(attempts__gte=settings.NOTIFICATION_MAX_ATTEMPTS).count()
        overdue = pending.filter(created_at__lt=timezone.now() - timedelta(minutes=30)).count()
        self.stdout.write(f"Pending: {pending.count()}; exhausted: {failed}; older than 30 minutes: {overdue}")
        if failed or overdue:
            raise CommandError("Review Notification jobs in Django admin; correct the cause before retrying.")
