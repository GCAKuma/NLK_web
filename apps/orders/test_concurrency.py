from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import uuid
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import Client, TransactionTestCase

from cart.models import Cart, CartItem
from content.models import SiteSettings
from products.models import Category, Product, ProductVariant
from orders.models import Order


@skipUnless(connection.vendor == "postgresql", "Row-lock verification requires PostgreSQL")
class ConcurrentCheckoutTests(TransactionTestCase):
    def setUp(self):
        SiteSettings.get_solo()
        category = Category.objects.create(name="Concurrency", slug="concurrency")
        product = Product.objects.create(category=category, name="Last item", slug="last-item")
        self.variant = ProductVariant.objects.create(product=product, sku="LAST", price=Decimal("10"), stock_quantity=1)

    def buyer(self, email, token=None):
        user = get_user_model().objects.create_user(email=email, password="test-password")
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=1)
        client = Client()
        client.force_login(user)
        session = client.session
        session["checkout_token"] = token or str(uuid.uuid4())
        session.save()
        return client, session["checkout_token"]

    def submit_together(self, buyers):
        barrier = Barrier(2)
        def submit(buyer):
            client, token = buyer
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return client.post("/orders/checkout/", {
                    "checkout_token": token, "full_name": "Buyer", "phone_number": "0770000000",
                    "address_line1": "Test street", "city": "Colombo", "district": "Colombo",
                    "postal_code": "10000", "payment_method": "cod",
                }).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(submit, buyers))

    def test_two_customers_cannot_buy_the_last_item(self):
        responses = self.submit_together([self.buyer("one@test.invalid"), self.buyer("two@test.invalid")])
        self.assertEqual(sorted(responses), [200, 302])
        self.assertEqual(Order.objects.count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 0)

    def test_simultaneous_duplicate_checkout_creates_one_order(self):
        first = self.buyer("same@test.invalid")
        second = Client()
        second.cookies = first[0].cookies.copy()
        responses = self.submit_together([first, (second, first[1])])
        self.assertEqual(responses, [302, 302])
        self.assertEqual(Order.objects.count(), 1)
