from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone

from orders.models import Order
from .models import Invoice, NotificationJob
from .outbox import enqueue_order, process_job, ready_jobs


class OutboxTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(email="outbox@test.invalid", password="test")
        self.order = Order.objects.create(user=user, subtotal=Decimal("10"), total=Decimal("10"))
        invoice = Invoice.objects.create(order=self.order, invoice_number="TEST-OUTBOX", generated_at=timezone.now())
        invoice.pdf_file.save("outbox.pdf", ContentFile(b"%PDF-test"))
        enqueue_order(self.order.pk)

    def test_email_retry_does_not_repeat_successful_recipient(self):
        customer = NotificationJob.objects.get(kind="customer_email")
        admin = NotificationJob.objects.get(kind="admin_email")
        self.assertEqual(process_job(customer.pk), "completed")
        with patch("notifications.delivery.EmailMessage.send", side_effect=OSError("SMTP down")):
            self.assertEqual(process_job(admin.pk), "failed")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(process_job(customer.pk), "skipped")
        NotificationJob.objects.filter(pk=admin.pk).update(available_at=timezone.now())
        self.assertEqual(process_job(admin.pk), "completed")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIsNotNone(Invoice.objects.get(order=self.order).emailed_at)

    def test_live_lease_prevents_duplicate_delivery_and_expired_lease_recovers(self):
        job = NotificationJob.objects.get(kind="customer_email")
        NotificationJob.objects.filter(pk=job.pk).update(lease_until=timezone.now()+timedelta(minutes=1))
        self.assertEqual(process_job(job.pk), "skipped")
        NotificationJob.objects.filter(pk=job.pk).update(lease_until=timezone.now()-timedelta(seconds=1))
        self.assertEqual(process_job(job.pk), "completed")
        self.assertEqual(len(mail.outbox), 1)

    def test_dependencies_and_retry_limit(self):
        invoice = NotificationJob.objects.get(kind="invoice")
        NotificationJob.objects.filter(pk=invoice.pk).update(completed_at=None)
        self.assertFalse(ready_jobs().filter(kind="customer_email").exists())
        NotificationJob.objects.filter(pk=invoice.pk).update(attempts=8)
        self.assertFalse(ready_jobs().exists())

    def test_legacy_emailed_invoice_is_not_resent(self):
        NotificationJob.objects.update(depends_on=None)
        NotificationJob.objects.all().delete()
        Invoice.objects.filter(order=self.order).update(emailed_at=timezone.now())
        enqueue_order(self.order.pk)
        self.assertFalse(ready_jobs().exists())

    def test_dispatcher_reservation_does_not_prevent_worker_delivery(self):
        with patch("notifications.tasks.process_notification_job.delay", side_effect=process_job):
            call_command("dispatch_notifications", once=True)
        self.assertEqual(len(mail.outbox), 2)
        self.assertFalse(ready_jobs().exists())

    def test_dispatcher_broker_failure_remains_recoverable(self):
        with patch("notifications.tasks.process_notification_job.delay", side_effect=ConnectionError("offline")):
            with self.assertRaises(ConnectionError):
                call_command("dispatch_notifications", once=True)
        self.assertEqual(ready_jobs().count(), 2)
        self.assertFalse(NotificationJob.objects.filter(published_until__isnull=False).exists())
