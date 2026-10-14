import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
from django.db.models import Q
from django.utils import timezone

from notifications.outbox import ready_jobs
from notifications.models import NotificationJob
from notifications.tasks import process_notification_job


class Command(BaseCommand):
    help = "Publish committed outbox jobs; safe to restart after a broker outage."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=int, default=10)

    def handle(self, *args, **options):
        while True:
            if not connection.in_atomic_block:
                close_old_connections()
            try:
                unpublished = ready_jobs().filter(Q(published_until__isnull=True) | Q(published_until__lt=timezone.now()))
                for job_id in unpublished.values_list("id", flat=True)[:100]:
                    # Reserve publication briefly; a process crash or a lost
                    # broker message becomes eligible again automatically.
                    reserved = ready_jobs().filter(pk=job_id).filter(
                        Q(published_until__isnull=True) | Q(published_until__lt=timezone.now())
                    ).update(
                        published_until=timezone.now() + timedelta(seconds=60),
                    )
                    if reserved:
                        try:
                            process_notification_job.delay(job_id)
                        except Exception:
                            NotificationJob.objects.filter(pk=job_id).update(published_until=None)
                            raise
            except Exception as exc:
                self.stderr.write(f"Dispatcher will retry: {type(exc).__name__}")
                if options["once"]:
                    raise
            if options["once"]:
                return
            time.sleep(max(1, options["interval"]))
