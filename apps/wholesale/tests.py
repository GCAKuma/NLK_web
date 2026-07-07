from django.test import TestCase
from django.urls import reverse

from .models import QuotationRequest


class QuotationRequestTests(TestCase):
    def test_submit_creates_request(self):
        resp = self.client.post(
            reverse("wholesale:quotation"),
            {
                "contact_name": "Mr Perera",
                "organization_name": "Royal College",
                "organization_type": "school",
                "email": "proc@royal.lk",
                "phone": "0771112222",
                "requirements": "200 x FX-991ES Plus",
            },
        )
        self.assertRedirects(resp, reverse("wholesale:quotation"))
        self.assertEqual(QuotationRequest.objects.count(), 1)
        q = QuotationRequest.objects.get()
        self.assertEqual(q.status, QuotationRequest.Status.NEW)
        self.assertEqual(q.organization_type, "school")

    def test_invalid_submission_rejected(self):
        resp = self.client.post(reverse("wholesale:quotation"), {"contact_name": "X"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(QuotationRequest.objects.count(), 0)
