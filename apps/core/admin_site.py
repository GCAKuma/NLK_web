"""Custom admin site that adds a business dashboard to the admin index."""
import logging

from django.contrib.admin import AdminSite
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 5


class NLKAdminSite(AdminSite):
    site_header = "NLK Control Panel"
    site_title = "NLK Admin"
    index_title = "Dashboard"
    index_template = "admin/dashboard.html"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            extra_context.update(self._dashboard())
        except Exception:  # never let dashboard stats break the admin
            logger.exception("Admin dashboard stats failed to load")
        return super().index(request, extra_context)

    def _dashboard(self):
        from django.db.models import Sum

        from orders.models import Order, PaymentProof
        from products.models import Product, ProductQuestion, ProductVariant
        from wholesale.models import QuotationRequest

        now = timezone.now()
        orders = Order.objects

        revenue_month = (
            orders.filter(created_at__year=now.year, created_at__month=now.month)
            .exclude(status=Order.Status.CANCELLED)
            .aggregate(total=Sum("total"))["total"]
            or 0
        )

        kpis = [
            {"label": "Orders today", "value": orders.filter(created_at__date=now.date()).count()},
            {"label": "Revenue this month", "value": f"Rs. {revenue_month:,.0f}"},
            {"label": "Total orders", "value": orders.count()},
            {"label": "Active products", "value": Product.objects.filter(is_active=True).count()},
        ]

        def link(name, query=""):
            return reverse(name) + query

        alerts = [
            {
                "label": "Payment slips to verify",
                "count": PaymentProof.objects.filter(status=PaymentProof.Status.PENDING).count(),
                "url": link("admin:orders_paymentproof_changelist", "?status__exact=pending"),
            },
            {
                "label": "Orders awaiting verification",
                "count": orders.filter(status=Order.Status.PAYMENT_VERIFICATION).count(),
                "url": link("admin:orders_order_changelist", "?status__exact=payment_verification"),
            },
            {
                "label": "Unanswered questions",
                "count": ProductQuestion.objects.filter(status=ProductQuestion.Status.PENDING).count(),
                "url": link("admin:products_productquestion_changelist", "?status__exact=pending"),
            },
            {
                "label": "New wholesale quotations",
                "count": QuotationRequest.objects.filter(status=QuotationRequest.Status.NEW).count(),
                "url": link("admin:wholesale_quotationrequest_changelist", "?status__exact=new"),
            },
            {
                "label": f"Low stock (≤ {LOW_STOCK_THRESHOLD})",
                "count": ProductVariant.objects.filter(
                    is_active=True, stock_quantity__lte=LOW_STOCK_THRESHOLD
                ).count(),
                "url": link("admin:products_productvariant_changelist"),
            },
        ]

        return {
            "nlk_kpis": kpis,
            "nlk_alerts": alerts,
            "nlk_recent_orders": list(orders.select_related("user")[:8]),
            "nlk_orders_url": link("admin:orders_order_changelist"),
        }
