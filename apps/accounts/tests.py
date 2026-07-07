from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_with_email(self):
        user = User.objects.create_user(email="Test@Example.com", password="pass12345")
        self.assertEqual(user.email, "Test@example.com")  # domain normalized
        self.assertTrue(user.check_password("pass12345"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@nlk.lk", password="pass12345")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_superuser_must_have_flags(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="a@nlk.lk", password="x", is_superuser=False
            )

    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, [])


class RegistrationFlowTests(TestCase):
    def test_register_creates_and_logs_in_user(self):
        response = self.client.post(
            "/accounts/register/",
            {
                "full_name": "Nimal Perera",
                "email": "nimal@example.com",
                "phone_number": "0770000000",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="nimal@example.com").exists())
        # Authenticated session established
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@example.com", password="StrongPass123")
        response = self.client.post(
            "/accounts/register/",
            {
                "full_name": "Dup",
                "email": "dup@example.com",
                "phone_number": "0770000000",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with error
        self.assertContains(response, "already exists")
