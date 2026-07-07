from django.contrib import admin

from .models import QuotationRequest


@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name", "contact_name", "organization_type",
        "phone", "status", "created_at",
    )
    list_filter = ("status", "organization_type", "created_at")
    list_editable = ("status",)
    search_fields = ("organization_name", "contact_name", "email", "phone")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
