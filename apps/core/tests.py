"""Regression coverage for shared templates and responsive UI state contracts."""
from decimal import Decimal
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Address
from cart.models import Cart, CartItem
from products.models import Category, Product, ProductVariant, CalculatorRecommendation


class DocumentIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "id":
                self.ids.append(value)


class StorefrontPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="ui@example.test", password="Test-password-123", full_name="UI Buyer"
        )
        cls.category = Category.objects.create(name="Calculators", slug="calculators")
        cls.product = Product.objects.create(
            name="Scientific calculator", slug="scientific-calculator",
            category=cls.category, is_featured=True,
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product, sku="UI-1", price=Decimal("2500"), stock_quantity=3,
        )
        CalculatorRecommendation.objects.create(
            student_type="al", recommended_product=cls.product,
        )

    def test_public_pages_render_shared_navigation(self):
        for url in ["/", "/shop/", "/category/calculators/", self.product.get_absolute_url(),
                    "/tools/compare/", "/tools/calculator-finder/", "/wholesale/",
                    "/about/", "/contact/", "/accounts/login/", "/accounts/register/",
                    "/accounts/password-reset/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="mobile-menu"')
                self.assertContains(response, 'id="main-content"')

    def test_finder_fragment_refreshes_selected_choice_with_results(self):
        response = self.client.get(
            reverse("products:calculator_finder"), {"type": "al"}, HTTP_HX_REQUEST="true"
        )
        self.assertContains(response, 'aria-pressed="true"', count=1)
        self.assertContains(response, "Your recommended options")
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, "<html")

    def test_out_of_stock_card_does_not_offer_purchase(self):
        self.variant.stock_quantity = 0
        self.variant.save()
        self.client.force_login(self.user)
        response = self.client.get("/shop/")
        self.assertContains(response, "Out of stock")
        self.assertNotContains(response, 'action="/cart/add/"')

    def test_account_labels_have_unique_targets(self):
        Address.objects.create(user=self.user, full_name="UI Buyer", phone_number="0770000000",
                               address_line1="1 Test Street", city="Colombo", district="Colombo")
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        parser = DocumentIds()
        parser.feed(response.content.decode())
        self.assertEqual(len(parser.ids), len(set(parser.ids)))

    def test_checkout_field_errors_are_visible(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=1)
        response = self.client.post(reverse("orders:checkout"), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please check the highlighted details.")
        self.assertContains(response, 'id="id_full_name_error"')
        self.assertContains(response, "This field is required.")
