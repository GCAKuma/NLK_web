"""Invoice PDF rendering (WeasyPrint)."""
from django.core.files.base import ContentFile
from django.template.loader import render_to_string


def invoice_number_for(order):
    """Deterministic, unique invoice number derived from the order number."""
    return f"INV-{order.order_number.replace('NLK-', '')}"


def render_invoice_pdf(order, invoice_number):
    """Render the invoice template to PDF bytes wrapped in a ContentFile.

    WeasyPrint is imported lazily so the module stays importable in
    environments where the native libs aren't present (e.g. tooling).
    """
    from weasyprint import HTML

    from content.models import SiteSettings

    html = render_to_string(
        "notifications/invoice.html",
        {
            "order": order,
            "invoice_number": invoice_number,
            "site": SiteSettings.get_solo(),
            "items": order.items.all(),
        },
    )
    pdf_bytes = HTML(string=html).write_pdf()
    return ContentFile(pdf_bytes)
