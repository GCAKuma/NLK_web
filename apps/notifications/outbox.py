"""Database-backed delivery tracking; callers enqueue in their business transaction."""
from datetime import timedelta
import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import NotificationJob

logger = logging.getLogger(__name__)


def enqueue(kind, object_id, depends_on=None, completed_at=None):
    job, _ = NotificationJob.objects.get_or_create(
        key=f"{kind}:{object_id}",
        defaults={"kind": kind, "object_id": object_id, "depends_on": depends_on, "completed_at": completed_at},
    )
    return job


def enqueue_order(order_id):
    from .models import Invoice
    existing = Invoice.objects.filter(order_id=order_id).first()
    generated = existing.generated_at if existing and existing.pdf_file else None
    emailed = existing.emailed_at if existing else None
    invoice = enqueue("invoice", order_id, completed_at=generated)
    enqueue("customer_email", order_id, invoice, completed_at=emailed)
    enqueue("admin_email", order_id, invoice, completed_at=emailed)
    if settings.WHATSAPP_PROVIDER != "console":
        enqueue("order_whatsapp", order_id)


def enqueue_quotation(quotation_id):
    enqueue("quotation_email", quotation_id)
    if settings.WHATSAPP_PROVIDER != "console":
        enqueue("quotation_whatsapp", quotation_id)


def ready_jobs():
    now = timezone.now()
    return NotificationJob.objects.filter(
        completed_at__isnull=True, attempts__lt=settings.NOTIFICATION_MAX_ATTEMPTS,
        available_at__lte=now,
    ).filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now)).filter(
        Q(depends_on__isnull=True) | Q(depends_on__completed_at__isnull=False)
    ).order_by("available_at", "pk")


def process_job(job_id):
    token = uuid.uuid4()
    with transaction.atomic():
        job = NotificationJob.objects.select_for_update().get(pk=job_id)
        if not ready_jobs().filter(pk=job_id).exists():
            return "skipped"
        job.attempts += 1
        job.lease_token = token
        job.lease_until = timezone.now() + timedelta(minutes=5)
        job.save(update_fields=["attempts", "lease_token", "lease_until", "updated_at"])

    try:
        from .delivery import deliver
        deliver(job)
    except Exception as exc:
        # Avoid storing recipient information/provider response bodies in logs.
        error = type(exc).__name__[:120]
        NotificationJob.objects.filter(pk=job.pk, lease_token=token).update(
            lease_until=None, lease_token=None, published_until=None, last_error=error,
            available_at=timezone.now() + timedelta(seconds=min(30 * 2 ** job.attempts, 3600)),
        )
        logger.error("Notification job %s failed (%s), attempt %s", job.pk, error, job.attempts)
        return "failed"
    NotificationJob.objects.filter(pk=job.pk, lease_token=token).update(
        completed_at=timezone.now(), lease_until=None, lease_token=None, last_error="",
    )
    if job.kind in {"customer_email", "admin_email"}:
        from .models import Invoice
        delivered = NotificationJob.objects.filter(
            kind__in=["customer_email", "admin_email"], object_id=job.object_id,
            completed_at__isnull=False,
        ).count()
        if delivered == 2:
            Invoice.objects.filter(order_id=job.object_id).update(emailed_at=timezone.now())
    return "completed"
