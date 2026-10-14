from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart
from content.models import SiteSettings
from products.models import Category, Product, ProductVariant

from .models import Order

User = get_user_model()


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@nlk.lk", password="StrongPass123", full_name="Buyer"
        )
        s = SiteSettings.get_solo()
        s.flat_shipping_fee = Decimal("400.00")
        s.save()
        cat = Category.objects.create(name="Calc", slug="calc")
        self.product = Product.objects.create(category=cat, name="FX", slug="fx")
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="FX-1", price=Decimal("2500.00"), stock_quantity=5
        )
        self.client.force_login(self.user)

    def _checkout_payload(self, method="cod"):
        self.client.get(reverse("orders:checkout"))
        return {
            "checkout_token": self.client.session.get("checkout_token", ""),
            "full_name": "Buyer", "phone_number": "0770000000",
            "address_line1": "1 Main St", "address_line2": "",
            "city": "Colombo", "district": "Colombo", "postal_code": "10000",
            "payment_method": method, "customer_notes": "leave at door",
        }

    def test_add_to_cart(self):
        resp = self.client.post(
            reverse("cart:add"), {"variant_id": self.variant.id, "quantity": 2}
        )
        self.assertRedirects(resp, reverse("cart:detail"))
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.item_count, 2)
        self.assertEqual(cart.subtotal, Decimal("5000.00"))

    def test_add_capped_to_stock(self):
        self.client.post(
            reverse("cart:add"), {"variant_id": self.variant.id, "quantity": 99}
        )
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.item_count, 5)  # capped at stock

    def test_cod_checkout_creates_confirmed_order(self):
        self.client.post(
            reverse("cart:add"), {"variant_id": self.variant.id, "quantity": 2}
        )
        resp = self.client.post(reverse("orders:checkout"), self._checkout_payload("cod"))
        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            resp, reverse("orders:confirmation", args=[order.order_number])
        )
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.subtotal, Decimal("5000.00"))
        self.assertEqual(order.shipping_fee, Decimal("400.00"))
        self.assertEqual(order.total, Decimal("5400.00"))

        # snapshots
        item = order.items.get()
        self.assertEqual(item.product_name_snapshot, "FX")
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("2500.00"))
        self.assertEqual(item.line_total, Decimal("5000.00"))

        # cart cleared + stock decremented + history logged
        self.assertEqual(Cart.objects.get(user=self.user).items.count(), 0)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 3)
        self.assertTrue(order.status_history.exists())

    def test_bank_deposit_checkout_is_pending(self):
        self.client.post(
            reverse("cart:add"), {"variant_id": self.variant.id, "quantity": 1}
        )
        self.client.post(reverse("orders:checkout"), self._checkout_payload("bank_deposit"))
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_invalid_payment_slip_keeps_validation_visible(self):
        self.client.post(reverse("cart:add"), {"variant_id": self.variant.id})
        self.client.post(reverse("orders:checkout"), self._checkout_payload("bank_deposit"))
        order = Order.objects.get(user=self.user)
        response = self.client.post(reverse("orders:upload_slip", args=[order.order_number]), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_checkout_empty_cart_redirects(self):
        resp = self.client.post(reverse("orders:checkout"), self._checkout_payload())
        self.assertRedirects(resp, reverse("cart:detail"))
        self.assertFalse(Order.objects.exists())

    def test_snapshot_survives_product_change(self):
        self.client.post(
            reverse("cart:add"), {"variant_id": self.variant.id, "quantity": 1}
        )
        self.client.post(reverse("orders:checkout"), self._checkout_payload("cod"))
        # Change the product after ordering
        self.product.name = "FX RENAMED"
        self.product.save()
        self.variant.price = Decimal("9999.00")
        self.variant.save()
        item = Order.objects.get(user=self.user).items.get()
        self.assertEqual(item.product_name_snapshot, "FX")
        self.assertEqual(item.unit_price, Decimal("2500.00"))

    def test_stock_change_after_cart_is_rejected(self):
        self.client.post(reverse("cart:add"), {"variant_id": self.variant.pk, "quantity": 3})
        payload = self._checkout_payload()
        self.variant.stock_quantity = 1
        self.variant.save()
        response = self.client.post(reverse("orders:checkout"), payload)
        self.assertContains(response, "no longer available")
        self.assertFalse(Order.objects.exists())
        self.assertEqual(Cart.objects.get(user=self.user).items.get().quantity, 3)

    def test_repeated_checkout_returns_existing_order(self):
        self.client.post(reverse("cart:add"), {"variant_id": self.variant.pk})
        payload = self._checkout_payload()
        first = self.client.post(reverse("orders:checkout"), payload)
        second = self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(first.url, second.url)
        self.assertEqual(Order.objects.count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 4)

    def test_order_and_outbox_commit_without_a_broker(self):
        from unittest.mock import patch
        from notifications.models import NotificationJob
        self.client.post(reverse("cart:add"), {"variant_id": self.variant.pk})
        payload = self._checkout_payload()
        with patch("celery.app.task.Task.apply_async", side_effect=ConnectionError("offline")):
            self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(NotificationJob.objects.count(), 3)

    def test_missing_checkout_token_cannot_place_order(self):
        self.client.post(reverse("cart:add"), {"variant_id": self.variant.pk})
        payload = self._checkout_payload()
        payload.pop("checkout_token")
        self.assertContains(self.client.post(reverse("orders:checkout"), payload), "checkout has expired")
        self.assertFalse(Order.objects.exists())


class AuthGateTests(TestCase):
    def test_cart_requires_login(self):
        resp = self.client.get(reverse("cart:detail"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_checkout_requires_login(self):
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)
