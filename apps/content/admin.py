from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import HeroSlide, SiteSettings, Testimonial, TrustStat, VideoEmbed


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin):
    fieldsets = (
        ("WhatsApp", {
            "fields": ("whatsapp_business_number", "admin_notification_whatsapp_number"),
        }),
        ("Contact", {"fields": ("contact_phone", "contact_email", "contact_address")}),
        ("Shipping", {"fields": ("flat_shipping_fee",)}),
        ("Social links", {
            "fields": ("facebook_url", "instagram_url", "tiktok_url", "youtube_url", "messenger_url"),
        }),
        ("Trust stats", {
            "fields": ("follower_count", "review_count", "video_view_count", "recommendation_percentage"),
        }),
    )


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    search_fields = ("title", "subtitle")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "source", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("source", "is_active")
    search_fields = ("customer_name", "quote")


@admin.register(VideoEmbed)
class VideoEmbedAdmin(admin.ModelAdmin):
    list_display = ("__str__", "platform", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("platform", "is_active")


@admin.register(TrustStat)
class TrustStatAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "display_order", "is_active")
    list_editable = ("value", "display_order", "is_active")
