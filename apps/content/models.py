from django.db import models
from solo.models import SingletonModel

from core.models import TimeStampedModel


class SiteSettings(SingletonModel):
    """Single editable row of site-wide settings (enforced by django-solo)."""

    # WhatsApp
    whatsapp_business_number = models.CharField(
        max_length=20, blank=True,
        help_text="Customer-facing WhatsApp number, digits only e.g. 9477XXXXXXX.",
    )
    admin_notification_whatsapp_number = models.CharField(
        max_length=20, blank=True,
        help_text="Where new-order/quotation alerts are sent.",
    )

    # Contact
    contact_phone = models.CharField(max_length=30, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_address = models.TextField(blank=True)

    # Shipping
    flat_shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Flat rate applied to every order.",
    )

    # Social links
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    messenger_url = models.URLField(blank=True)

    # Trust stats (stored as display strings, e.g. "12,000+")
    follower_count = models.CharField(max_length=50, blank=True)
    review_count = models.CharField(max_length=50, blank=True)
    video_view_count = models.CharField(max_length=50, blank=True)
    recommendation_percentage = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Site Settings"

    def __str__(self):
        return "Site Settings"


class HeroSlide(TimeStampedModel):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    bullet_points = models.TextField(
        blank=True, help_text="One bullet per line."
    )
    image = models.ImageField(upload_to="hero/", blank=True)
    button_text = models.CharField(max_length=60, blank=True)
    button_link = models.CharField(max_length=300, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title

    @property
    def bullets(self):
        return [b.strip() for b in self.bullet_points.splitlines() if b.strip()]


class Testimonial(TimeStampedModel):
    customer_name = models.CharField(max_length=150)
    quote = models.TextField(blank=True)
    screenshot_image = models.ImageField(upload_to="testimonials/", blank=True)
    source = models.CharField(
        max_length=60, blank=True, help_text='e.g. "Facebook"'
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.customer_name} ({self.source})"


class VideoEmbed(TimeStampedModel):
    class Platform(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        REELS = "reels", "Reels"

    platform = models.CharField(max_length=20, choices=Platform.choices)
    embed_url_or_code = models.TextField(help_text="Embed URL or embed code.")
    thumbnail = models.ImageField(upload_to="videos/", blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.get_platform_display()} video #{self.pk}"


class TrustStat(TimeStampedModel):
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=50)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.label}: {self.value}"
