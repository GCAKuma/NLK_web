from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class Cart(TimeStampedModel):
    """One persistent cart per user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )

    def __str__(self):
        return f"Cart({self.user.email})"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(
            (item.line_total for item in self.items.all()), Decimal("0.00")
        )


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product_variant"], name="uniq_cart_variant"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="cartitem_quantity_positive"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_variant.sku}"

    @property
    def unit_price(self):
        return self.product_variant.price

    @property
    def line_total(self):
        return self.product_variant.price * self.quantity
