from django.shortcuts import render

from content.models import HeroSlide, Testimonial, TrustStat, VideoEmbed
from products.models import Category, Product


def home(request):
    """Daraz-style homepage, driven entirely by admin-managed content."""
    context = {
        "hero_slides": HeroSlide.objects.filter(is_active=True),
        "categories": Category.objects.filter(is_active=True, parent__isnull=True),
        "best_sellers": Product.objects.filter(
            is_active=True, is_featured=True
        ).select_related("category")[:8],
        "testimonials": Testimonial.objects.filter(is_active=True),
        "videos": VideoEmbed.objects.filter(is_active=True),
        "trust_stats": TrustStat.objects.filter(is_active=True),
    }
    return render(request, "home.html", context)


def about(request):
    return render(request, "about.html")


def contact(request):
    return render(request, "contact.html")


def coming_soon(request, feature="This feature"):
    """Generic 'coming soon' page for links to not-yet-built sections."""
    return render(request, "coming_soon.html", {"feature": feature})
