from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "generated_at", "emailed_at")
    search_fields = ("invoice_number", "order__order_number")
    autocomplete_fields = ("order",)
    readonly_fields = ("generated_at", "emailed_at", "created_at", "updated_at")
