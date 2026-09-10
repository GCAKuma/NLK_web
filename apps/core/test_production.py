from tempfile import TemporaryDirectory
from unittest.mock import patch
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.db import connection
from django.core.management import call_command

from notifications.models import Invoice
from orders.models import Order
from products.models import Category, Product, ProductVariant, ProductImage


class PrivateFileTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.directory.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = get_user_model().objects.create_user(email="owner@test.invalid", password="test")
        self.other = get_user_model().objects.create_user(email="other@test.invalid", password="test")
        order = Order.objects.create(user=self.owner)
        self.invoice = Invoice.objects.create(order=order, invoice_number="PRIVATE-TEST")
        self.invoice.pdf_file.save("private-test.pdf", ContentFile(b"%PDF-private-test"))

    def test_private_url_requires_owner_and_never_allows_shared_caching(self):
        url = self.invoice.pdf_file.url
        self.assertTrue(url.startswith("/private-media/invoices/"))
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-private-test")
        self.assertIn("no-store", response["Cache-Control"])
        response.close()

    def test_legacy_media_url_cannot_bypass_authorization(self):
        url = "/media/" + self.invoice.pdf_file.name
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)


class HealthTests(TestCase):
    def test_readiness_reports_dependency_failure_without_details(self):
        self.assertEqual(self.client.get("/health/live/").status_code, 200)
        with patch("core.production_views.cache.set", side_effect=ConnectionError("secret")):
            response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "secret", status_code=503)


class ProductQueryTests(TestCase):
    def test_prefetched_cards_do_not_query_per_product(self):
        category = Category.objects.create(name="Test", slug="test")
        product = Product.objects.create(category=category, name="Test", slug="test")
        ProductVariant.objects.create(product=product, sku="QUERY", price=10, stock_quantity=2)
        ProductImage.objects.create(product=product, image="products/test.jpg", is_primary=True)
        products = list(Product.objects.prefetch_related("images", "variants"))
        with self.assertNumQueries(0):
            for product in products:
                self.assertTrue(product.primary_image)
                self.assertTrue(product.in_stock)
                self.assertEqual(product.display_price, 10)
                self.assertEqual(product.variants.count(), 1)


@skipUnless(connection.vendor == "postgresql", "Runtime permission checks require PostgreSQL")
class RuntimePermissionTests(TestCase):
    def test_runtime_role_reads_rls_tables_but_cannot_create_tables(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE ROLE nlk_permission_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS")
        call_command("secure_application_tables", runtime_role="nlk_permission_test")
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE nlk_permission_test")
            cursor.execute("SELECT count(*) FROM accounts_user")
            cursor.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute("SELECT has_table_privilege(current_user, 'products_product', 'UPDATE')")
            self.assertTrue(cursor.fetchone()[0])
            cursor.execute("SELECT has_table_privilege(current_user, 'products_product', 'TRUNCATE')")
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute("RESET ROLE")
