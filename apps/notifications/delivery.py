"""External side effects invoked only by a leased notification job."""
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def deliver(job):
    from orders.models import Order
    from content.models import SiteSettings
    from wholesale.models import QuotationRequest
    from .services import get_whatsapp_provider, build_new_order_message
    from .tasks import generate_invoice

    if job.kind == "invoice":
        generate_invoice.run(job.object_id)
        return
    if job.kind in {"customer_email", "admin_email", "order_whatsapp"}:
        order = Order.objects.select_related("user").get(pk=job.object_id)
        if job.kind == "order_whatsapp":
            sent = get_whatsapp_provider().send(
                SiteSettings.get_solo().admin_notification_whatsapp_number,
                build_new_order_message(order),
            )
            if not sent:
                raise RuntimeError("WhatsApp delivery is not configured")
            return
        customer = job.kind == "customer_email"
        role = "customer" if customer else "admin"
        subject = f"Your NLK order {order.order_number}" if customer else f"New order {order.order_number}"
        message = EmailMessage(
            subject,
            render_to_string(f"notifications/email/order_confirmation_{role}.txt", {"order": order}),
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email if customer else settings.ADMIN_EMAIL],
        )
        invoice = order.invoice
        if not invoice.generated_at or not invoice.pdf_file:
            raise RuntimeError("Invoice is not ready")
        with invoice.pdf_file.open("rb") as pdf:
            message.attach(f"{invoice.invoice_number}.pdf", pdf.read(), "application/pdf")
        message.send(fail_silently=False)
        return
    quote = QuotationRequest.objects.get(pk=job.object_id)
    if job.kind == "quotation_email":
        EmailMessage(
            f"New wholesale quotation: {quote.organization_name}",
            render_to_string("notifications/email/quotation_admin.txt", {"q": quote}),
            settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL],
        ).send(fail_silently=False)
    elif job.kind == "quotation_whatsapp":
        sent = get_whatsapp_provider().send(
            SiteSettings.get_solo().admin_notification_whatsapp_number,
            f"New wholesale quotation: {quote.organization_name}\nContact: {quote.contact_name} · {quote.phone}",
        )
        if not sent:
            raise RuntimeError("WhatsApp delivery is not configured")
    else:
        raise ValueError("Unknown notification kind")
