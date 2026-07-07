from django.db import models

from core.models import TimeStampedModel


class QuotationRequest(TimeStampedModel):
    """A wholesale/institutional quotation enquiry (not a cart purchase)."""

    class OrganizationType(models.TextChoices):
        SCHOOL = "school", "School"
        BOOKSHOP = "bookshop", "Bookshop"
        GOVERNMENT = "government", "Government Institution"
        UNIVERSITY = "university", "University"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUOTED = "quoted", "Quoted"
        CLOSED = "closed", "Closed"

    contact_name = models.CharField(max_length=150)
    organization_name = models.CharField(max_length=200)
    organization_type = models.CharField(
        max_length=20, choices=OrganizationType.choices
    )
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    requirements = models.TextField(help_text="Items or requirements requested.")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization_name} ({self.get_status_display()})"
