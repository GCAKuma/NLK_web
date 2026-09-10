import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cart.views import get_user_cart
from content.models import SiteSettings
from cart.models import Cart
from products.models import ProductVariant
from notifications.outbox import enqueue_order

from .forms import CheckoutForm, PaymentProofForm
from .models import Order, OrderItem, OrderStatusHistory, PaymentProof


@login_required
def checkout(request):
    cart = get_user_cart(request.user)
    token = request.session.get("checkout_token")
    if request.method == "POST":
        try:
            posted_token = uuid.UUID(request.POST.get("checkout_token", ""))
        except (ValueError, TypeError, AttributeError):
            posted_token = None
        if posted_token:
            previous = Order.objects.filter(user=request.user, checkout_token=posted_token).first()
            if previous:
                return redirect("orders:confirmation", order_number=previous.order_number)
    items = cart.items.select_related("product_variant__product").all()
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("cart:detail")

    shipping_fee = SiteSettings.get_solo().flat_shipping_fee
    subtotal = cart.subtotal
    total = subtotal + shipping_fee

    address = getattr(request.user, "address", None)

    if request.method == "POST":
        form = CheckoutForm(request.POST, instance=address)
        if form.is_valid():
            if not posted_token or str(posted_token) != token:
                form.add_error(None, "This checkout has expired. Reload the page and try again.")
            else:
                try:
                    order = _place_order(request, cart, form, posted_token)
                except CheckoutUnavailable as exc:
                    form.add_error(None, str(exc))
                else:
                    messages.success(request, f"Order {order.order_number} placed successfully!")
                    return redirect("orders:confirmation", order_number=order.order_number)
    else:
        if not token or Order.objects.filter(user=request.user, checkout_token=token).exists():
            token = str(uuid.uuid4())
            request.session["checkout_token"] = token
        initial = {}
        if address is None:
            initial = {
                "full_name": request.user.full_name,
                "phone_number": request.user.phone_number,
            }
        form = CheckoutForm(instance=address, initial=initial)

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "checkout_token": token,
            "items": items,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total": total,
        },
    )


class CheckoutUnavailable(Exception):
    pass


@transaction.atomic
def _place_order(request, cart, form, checkout_token):
    # Cart mutations take this same lock. Sort variants to avoid deadlocks when
    # different customers check out overlapping products in different orders.
    cart = Cart.objects.select_for_update().get(pk=cart.pk, user=request.user)
    previous = Order.objects.filter(user=request.user, checkout_token=checkout_token).first()
    if previous:
        return previous
    items = list(cart.items.order_by("product_variant_id"))
    if not items:
        raise CheckoutUnavailable("Your cart is empty. Please add a product first.")
    variants = {
        v.pk: v for v in ProductVariant.objects.select_for_update(of=("self",))
        .select_related("product").filter(pk__in=[i.product_variant_id for i in items])
        .order_by("pk")
    }
    for item in items:
        variant = variants[item.product_variant_id]
        if not variant.is_active or not variant.product.is_active or item.quantity > variant.stock_quantity:
            raise CheckoutUnavailable(f"{variant.product.name} is no longer available in that quantity. Please update your cart.")
        item.product_variant = variant
    subtotal = sum((item.line_total for item in items), Decimal("0.00"))
    shipping_fee = SiteSettings.get_solo().flat_shipping_fee
    # Persist / update the customer's single saved address
    address = form.save(commit=False)
    address.user = request.user
    address.save()

    payment_method = form.cleaned_data["payment_method"]
    # COD can be confirmed immediately; bank deposits await a slip.
    if payment_method == Order.PaymentMethod.COD:
        status = Order.Status.CONFIRMED
    else:
        status = Order.Status.PENDING

    order = Order.objects.create(
        user=request.user,
        checkout_token=checkout_token,
        status=status,
        payment_method=payment_method,
        shipping_full_name=address.full_name,
        shipping_phone=address.phone_number,
        shipping_address_line1=address.address_line1,
        shipping_address_line2=address.address_line2,
        shipping_city=address.city,
        shipping_district=address.district,
        shipping_postal_code=address.postal_code,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=subtotal + shipping_fee,
        customer_notes=form.cleaned_data.get("customer_notes", ""),
    )

    for item in items:
        variant = item.product_variant
        OrderItem.objects.create(
            order=order,
            product_variant=variant,
            product_name_snapshot=variant.product.name,
            variant_label_snapshot=variant.label,
            unit_price=variant.price,
            quantity=item.quantity,
            line_total=item.line_total,
        )
        variant.stock_quantity -= item.quantity
        variant.save(update_fields=["stock_quantity"])

    OrderStatusHistory.objects.create(
        order=order, status=order.status, changed_by=request.user,
        note="Order placed.",
    )

    # Clear the cart
    cart.items.all().delete()

    # The database and durable jobs commit together; checkout never depends on
    # Redis being available. The dispatcher publishes committed jobs later.
    enqueue_order(order.id)

    return order


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_number=order_number,
        user=request.user,
    )
    proof_form = None
    if order.payment_method == Order.PaymentMethod.BANK_DEPOSIT:
        if not hasattr(order, "payment_proof"):
            proof_form = PaymentProofForm()
    return render(
        request,
        "orders/order_confirmation.html",
        {"order": order, "proof_form": proof_form, "just_placed": True},
    )


@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related("items").all()
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "status_history"),
        order_number=order_number,
        user=request.user,
    )
    proof_form = None
    if order.payment_method == Order.PaymentMethod.BANK_DEPOSIT and not hasattr(
        order, "payment_proof"
    ):
        proof_form = PaymentProofForm()
    return render(
        request,
        "orders/order_detail.html",
        {"order": order, "proof_form": proof_form},
    )


@login_required
def upload_slip(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if request.method == "POST":
        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            proof = form.save(commit=False)
            proof.order = order
            proof.save()
            if order.status == Order.Status.PENDING:
                order.status = Order.Status.PAYMENT_VERIFICATION
                order.save(update_fields=["status", "updated_at"])
                OrderStatusHistory.objects.create(
                    order=order, status=order.status, changed_by=request.user,
                    note="Payment slip uploaded by customer.",
                )
            messages.success(
                request, "Payment slip uploaded. We'll verify it and confirm your order."
            )
        else:
            return render(
                request,
                "orders/order_detail.html",
                {"order": order, "proof_form": form},
            )
    return redirect("orders:detail", order_number=order.order_number)
