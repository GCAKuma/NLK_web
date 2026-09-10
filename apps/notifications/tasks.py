"""Celery tasks for order notifications.

Each task is idempotent and retries on transient failure so the pipeline is
safe to re-run (e.g. after a worker restart or a redelivered message).
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_invoice(self, order_id: int):
    """Render and store the invoice PDF for an order (idempotent)."""
    from orders.models import Order

    from .invoices import invoice_number_for, render_invoice_pdf
    from .models import Invoice

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("generate_invoice: order %s not found", order_id)
        return {"order_id": order_id, "status": "missing"}

    invoice, _ = Invoice.objects.get_or_create(
        order=order, defaults={"invoice_number": invoice_number_for(order)}
    )
    if invoice.pdf_file and invoice.generated_at:
        return {"order_id": order_id, "status": "already_generated"}

    try:
        pdf = render_invoice_pdf(order, invoice.invoice_number)
    except Exception as exc:
        logger.exception("Invoice render failed for order %s", order_id)
        raise self.retry(exc=exc)

    invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", pdf, save=False)
    invoice.generated_at = timezone.now()
    invoice.save()
    return {"order_id": order_id, "status": "generated"}


@shared_task
def process_notification_job(job_id):
    from .outbox import process_job
    return process_job(job_id)


@shared_task
def send_order_emails(order_id: int):
    """Compatibility entry point; independent recipient jobs prevent repeat sends."""
    from .outbox import enqueue_order, process_job
    from .models import NotificationJob
    enqueue_order(order_id)
    invoice_job = NotificationJob.objects.get(key=f"invoice:{order_id}")
    process_job(invoice_job.pk)
    for kind in ("customer_email", "admin_email"):
        process_job(NotificationJob.objects.get(key=f"{kind}:{order_id}").pk)
    return {"order_id": order_id, "status": "processed"}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_admin_whatsapp(self, order_id: int):
    """Send a WhatsApp alert to the admin via the configured provider."""
    from content.models import SiteSettings
    from orders.models import Order

    from .services import build_new_order_message, get_whatsapp_provider

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("send_admin_whatsapp: order %s not found", order_id)
        return {"order_id": order_id, "status": "missing"}

    number = SiteSettings.get_solo().admin_notification_whatsapp_number
    try:
        get_whatsapp_provider().send(number, build_new_order_message(order))
    except Exception as exc:
        logger.exception("Admin WhatsApp failed for order %s", order_id)
        raise self.retry(exc=exc)
    return {"order_id": order_id, "status": "sent"}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_quotation_alert(self, quotation_id: int):
    """Email + WhatsApp the admin when a wholesale quotation is submitted."""
    from content.models import SiteSettings
    from wholesale.models import QuotationRequest

    from .services import get_whatsapp_provider

    try:
        q = QuotationRequest.objects.get(id=quotation_id)
    except QuotationRequest.DoesNotExist:
        logger.warning("send_quotation_alert: quotation %s not found", quotation_id)
        return {"quotation_id": quotation_id, "status": "missing"}

    body = render_to_string("notifications/email/quotation_admin.txt", {"q": q})
    try:
        EmailMessage(
            f"New wholesale quotation: {q.organization_name}",
            body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL],
        ).send(fail_silently=False)
    except Exception as exc:
        logger.exception("Quotation email failed for %s", quotation_id)
        raise self.retry(exc=exc)

    number = SiteSettings.get_solo().admin_notification_whatsapp_number
    message = (
        f"ðŸ“„ New wholesale quotation\n"
        f"Org: {q.organization_name} ({q.get_organization_type_display()})\n"
        f"Contact: {q.contact_name} Â· {q.phone}"
    )
    try:
        get_whatsapp_provider().send(number, message)
    except Exception:
        logger.exception("Quotation WhatsApp failed for %s", quotation_id)

    return {"quotation_id": quotation_id, "status": "sent"}
