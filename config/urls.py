from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core import production_views

# Admin branding + dashboard live on core.admin_site.NLKAdminSite.

urlpatterns = [
    path("health/live/", production_views.live, name="health_live"),
    path("health/ready/", production_views.ready, name="health_ready"),
    path("private-media/<path:name>", production_views.private_media, name="private_media"),
    path("media/invoices/<path:name>", production_views.legacy_invoice),
    path("media/payment_slips/<path:name>", production_views.legacy_slip),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("wholesale/", include("wholesale.urls")),
    path("", include("products.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
