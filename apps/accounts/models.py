from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user: email is the login identifier (no username)."""

    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password already required

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def get_short_name(self):
        return self.full_name or self.email.split("@")[0]

    def get_full_name(self):
        return self.full_name or self.email


class Address(TimeStampedModel):
    """A customer's single saved address (one per user)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="address",
    )
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.full_name} — {self.city}, {self.district}"
