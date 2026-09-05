import secrets
from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


def generate_order_number():
    """Human-friendly, collision-resistant order number: NLK-YYYYMMDD-XXXXXX."""
    return f"NLK-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAYMENT_VERIFICATION = "payment_verification", "Payment verification"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"
        BANK_DEPOSIT = "bank_deposit", "Bank Deposit"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    order_number = models.CharField(
        max_length=32, unique=True, default=generate_order_number, editable=False
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)

    # Shipping snapshot (copied at checkout; never a live FK to Address)
    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=20)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_district = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    customer_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(subtotal__gte=0), name="order_subtotal_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(shipping_fee__gte=0), name="order_shipping_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0), name="order_total_non_negative"
            ),
        ]

    def __str__(self):
        return self.order_number

    def recalculate_total(self):
        self.total = self.subtotal + self.shipping_fee
        return self.total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(
        "products.ProductVariant",
        null=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    # Snapshots so historical orders stay correct if the product/variant changes
    product_name_snapshot = models.CharField(max_length=200)
    variant_label_snapshot = models.CharField(max_length=200, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="orderitem_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0), name="orderitem_unit_price_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0), name="orderitem_line_total_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_name_snapshot}"


class PaymentProof(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment_proof"
    )
    slip_image = models.ImageField(upload_to="payment_slips/")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Slip for {self.order.order_number} ({self.status})"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_history"
    )
    status = models.CharField(max_length=30, choices=Order.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "order status histories"

    def __str__(self):
        return f"{self.order.order_number} → {self.status}"
