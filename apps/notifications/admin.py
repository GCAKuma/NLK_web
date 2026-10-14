from django.contrib import admin

from .models import Invoice, NotificationJob
from django.utils import timezone


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "generated_at", "emailed_at")
    search_fields = ("invoice_number", "order__order_number")
    autocomplete_fields = ("order",)
    readonly_fields = ("generated_at", "emailed_at", "created_at", "updated_at")


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = ("key", "attempts", "completed_at", "available_at", "last_error")
    list_filter = ("kind", "completed_at")
    readonly_fields = tuple(field.name for field in NotificationJob._meta.fields)
    actions = ["retry_failed"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Retry incomplete jobs whose lease has expired")
    def retry_failed(self, request, queryset):
        from django.db.models import Q
        count = queryset.filter(completed_at__isnull=True).filter(
            Q(lease_until__isnull=True) | Q(lease_until__lt=timezone.now())
        ).update(attempts=0, available_at=timezone.now(), lease_until=None, lease_token=None, published_until=None, last_error="")
        self.message_user(request, f"{count} jobs queued for retry.")
