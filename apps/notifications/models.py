from django.db import models

from core.models import TimeStampedModel


class Invoice(TimeStampedModel):
    """Generated invoice PDF for an order (PDF rendering wired in Milestone 5)."""

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="invoice"
    )
    invoice_number = models.CharField(max_length=32, unique=True)
    pdf_file = models.FileField(upload_to="invoices/", blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number
