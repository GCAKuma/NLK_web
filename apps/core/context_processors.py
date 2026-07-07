"""Template context processors making site-wide data available everywhere."""


def site_settings(request):
    """Expose the singleton SiteSettings to every template.

    Wrapped defensively so pages still render before migrations run or if the
    content app is unavailable.
    """
    settings_obj = None
    try:
        from content.models import SiteSettings

        settings_obj = SiteSettings.get_solo()
    except Exception:
        settings_obj = None
    return {"site_settings": settings_obj}


def cart_summary(request):
    """Expose the current user's cart item count for the header badge."""
    count = 0
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        try:
            from cart.models import Cart

            cart = Cart.objects.filter(user=user).first()
            if cart is not None:
                count = cart.item_count
        except Exception:
            count = 0
    return {"cart_item_count": count}
