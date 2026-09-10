from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def live(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        cache.set("nlk-readiness", True, 30)
        if not cache.get("nlk-readiness"):
            raise RuntimeError("Cache unavailable")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


@login_required
@never_cache
@require_GET
def private_media(request, name):
    from notifications.models import Invoice
    from orders.models import PaymentProof

    if name.startswith("invoices/"):
        queryset = Invoice.objects.filter(pdf_file=name)
        permission = "notifications.view_invoice"
        field = "pdf_file"
    elif name.startswith("payment_slips/"):
        queryset = PaymentProof.objects.filter(slip_image=name)
        permission = "orders.view_paymentproof"
        field = "slip_image"
    else:
        raise Http404
    if not (request.user.is_staff and request.user.has_perm(permission)):
        queryset = queryset.filter(order__user=request.user)
    record = queryset.first()
    if not record:
        raise Http404
    file = getattr(record, field)
    if hasattr(file.storage, "signed_url"):
        response = redirect(file.storage.signed_url(file.name))
    else:
        try:
            response = FileResponse(file.open("rb"), as_attachment=True)
        except FileNotFoundError:
            raise Http404
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


def legacy_invoice(request, name):
    return private_media(request, f"invoices/{name}")


def legacy_slip(request, name):
    return private_media(request, f"payment_slips/{name}")
