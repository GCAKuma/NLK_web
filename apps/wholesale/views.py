from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from notifications.tasks import send_quotation_alert

from .forms import QuotationRequestForm


def quotation(request):
    """Wholesale solutions landing page with a quotation request form."""
    if request.method == "POST":
        form = QuotationRequestForm(request.POST)
        if form.is_valid():
            quote = form.save()
            transaction.on_commit(lambda: send_quotation_alert.delay(quote.id))
            messages.success(
                request,
                "Thank you! Your quotation request has been received. "
                "Our team will contact you shortly.",
            )
            return redirect("wholesale:quotation")
    else:
        form = QuotationRequestForm()
    return render(request, "wholesale/quotation.html", {"form": form})
