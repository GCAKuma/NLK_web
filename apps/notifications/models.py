from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from core.storage import private_storage


class Invoice(TimeStampedModel):
    """Generated invoice PDF for an order (PDF rendering wired in Milestone 5)."""

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="invoice"
    )
    invoice_number = models.CharField(max_length=32, unique=True)
    pdf_file = models.FileField(upload_to="invoices/", blank=True, storage=private_storage)
    generated_at = models.DateTimeField(null=True, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number


class NotificationJob(TimeStampedModel):
    """Durable outbox; one record per external delivery or invoice operation."""

    key = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=40)
    object_id = models.PositiveBigIntegerField()
    depends_on = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    published_until = models.DateTimeField(null=True, blank=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.key
