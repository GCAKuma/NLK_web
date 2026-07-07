from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from orders.models import Order, OrderItem
from products.models import Category, Product, ProductVariant

from .models import Invoice
from .tasks import generate_invoice, send_admin_whatsapp, send_order_emails

User = get_user_model()


class NotificationTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="n@nlk.lk", password="x", full_name="Nimal"
        )
        cat = Category.objects.create(name="C", slug="c")
        product = Product.objects.create(category=cat, name="Widget", slug="widget")
        variant = ProductVariant.objects.create(
            product=product, sku="W-1", price=Decimal("1000.00"), stock_quantity=5
        )
        self.order = Order.objects.create(
            user=self.user, payment_method="cod", status="confirmed",
            shipping_full_name="Nimal", shipping_phone="0770000000",
            shipping_address_line1="1 Main St", shipping_city="Colombo",
            shipping_district="Colombo",
            subtotal=Decimal("1000.00"), shipping_fee=Decimal("400.00"),
            total=Decimal("1400.00"),
        )
        OrderItem.objects.create(
            order=self.order, product_variant=variant,
            product_name_snapshot="Widget", variant_label_snapshot="Default",
            unit_price=Decimal("1000.00"), quantity=1, line_total=Decimal("1000.00"),
        )

    def test_generate_invoice_pdf(self):
        generate_invoice.apply(args=[self.order.id])
        invoice = Invoice.objects.get(order=self.order)
        self.assertTrue(invoice.pdf_file)
        self.assertIsNotNone(invoice.generated_at)
        self.assertTrue(invoice.pdf_file.name.endswith(".pdf"))

    def test_generate_invoice_is_idempotent(self):
        generate_invoice.apply(args=[self.order.id])
        generate_invoice.apply(args=[self.order.id])
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 1)

    def test_send_order_emails_with_attachment(self):
        generate_invoice.apply(args=[self.order.id])
        send_order_emails.apply(args=[self.order.id])
        self.assertEqual(len(mail.outbox), 2)  # customer + admin
        # customer email carries the invoice PDF
        self.assertTrue(mail.outbox[0].attachments)
        self.assertEqual(mail.outbox[0].attachments[0][2], "application/pdf")
        invoice = Invoice.objects.get(order=self.order)
        self.assertIsNotNone(invoice.emailed_at)

    def test_send_order_emails_idempotent(self):
        generate_invoice.apply(args=[self.order.id])
        send_order_emails.apply(args=[self.order.id])
        send_order_emails.apply(args=[self.order.id])
        self.assertEqual(len(mail.outbox), 2)  # not re-sent

    def test_admin_whatsapp_console_provider(self):
        result = send_admin_whatsapp.apply(args=[self.order.id])
        self.assertEqual(result.result["status"], "sent")
