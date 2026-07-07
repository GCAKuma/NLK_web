from django.contrib import admin
from django.utils import timezone

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentProof,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = (
        "product_name_snapshot", "variant_label_snapshot",
        "unit_price", "quantity", "line_total",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class PaymentProofInline(admin.StackedInline):
    model = PaymentProof
    extra = 0
    readonly_fields = ("created_at", "verified_by", "verified_at")
    fields = ("slip_image", "status", "admin_notes", "verified_by", "verified_at", "created_at")


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ("status", "changed_by", "changed_at", "note")
    readonly_fields = fields
    ordering = ("-changed_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "user", "status", "payment_method",
        "total", "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("order_number", "user__email", "shipping_full_name", "shipping_phone")
    date_hierarchy = "created_at"
    readonly_fields = ("order_number", "subtotal", "shipping_fee", "total", "created_at", "updated_at")
    inlines = [OrderItemInline, PaymentProofInline, OrderStatusHistoryInline]

    fieldsets = (
        (None, {"fields": ("order_number", "user", "status", "payment_method", "customer_notes")}),
        ("Shipping (snapshot)", {
            "fields": (
                "shipping_full_name", "shipping_phone",
                "shipping_address_line1", "shipping_address_line2",
                "shipping_city", "shipping_district", "shipping_postal_code",
            )
        }),
        ("Totals", {"fields": ("subtotal", "shipping_fee", "total")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = (
                Order.objects.filter(pk=obj.pk)
                .values_list("status", flat=True)
                .first()
            )
        super().save_model(request, obj, form, change)
        if old_status != obj.status:
            OrderStatusHistory.objects.create(
                order=obj,
                status=obj.status,
                changed_by=request.user,
                note="Status changed via admin.",
            )


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "verified_by", "verified_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__order_number", "order__user__email")
    autocomplete_fields = ("order",)
    readonly_fields = ("verified_by", "verified_at", "created_at")
    actions = ["mark_verified", "mark_rejected"]

    @admin.action(description="Mark selected slips VERIFIED and confirm orders")
    def mark_verified(self, request, queryset):
        count = 0
        for proof in queryset:
            proof.status = PaymentProof.Status.VERIFIED
            proof.verified_by = request.user
            proof.verified_at = timezone.now()
            proof.save()
            order = proof.order
            if order.status in (
                Order.Status.PENDING,
                Order.Status.PAYMENT_VERIFICATION,
            ):
                order.status = Order.Status.CONFIRMED
                order.save(update_fields=["status", "updated_at"])
                OrderStatusHistory.objects.create(
                    order=order,
                    status=order.status,
                    changed_by=request.user,
                    note="Payment slip verified.",
                )
            count += 1
        self.message_user(request, f"{count} payment slip(s) verified.")

    @admin.action(description="Mark selected slips REJECTED")
    def mark_rejected(self, request, queryset):
        updated = queryset.update(
            status=PaymentProof.Status.REJECTED,
            verified_by=request.user,
            verified_at=timezone.now(),
        )
        self.message_user(request, f"{updated} payment slip(s) rejected.")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "changed_by", "changed_at")
    list_filter = ("status", "changed_at")
    search_fields = ("order__order_number",)
    readonly_fields = ("order", "status", "changed_by", "changed_at", "note")

    def has_add_permission(self, request):
        return False
