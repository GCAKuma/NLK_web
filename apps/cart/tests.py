from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from products.models import Category, Product, ProductVariant

from .models import Cart, CartItem

User = get_user_model()


class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="c@nlk.lk", password="x")
        self.cart = Cart.objects.create(user=self.user)
        cat = Category.objects.create(name="Calculators", slug="calc")
        product = Product.objects.create(category=cat, name="FX", slug="fx")
        self.variant = ProductVariant.objects.create(
            product=product, sku="FX-1", price=Decimal("2500.00"), stock_quantity=10
        )

    def test_line_total_and_subtotal(self):
        CartItem.objects.create(
            cart=self.cart, product_variant=self.variant, quantity=3
        )
        self.assertEqual(self.cart.subtotal, Decimal("7500.00"))
        self.assertEqual(self.cart.item_count, 3)

    def test_duplicate_variant_rejected(self):
        CartItem.objects.create(cart=self.cart, product_variant=self.variant, quantity=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart, product_variant=self.variant, quantity=1
                )
