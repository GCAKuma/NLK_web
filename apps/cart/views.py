from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from content.models import SiteSettings
from products.models import ProductVariant

from .models import Cart, CartItem


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_detail(request):
    cart = get_user_cart(request.user)
    items = cart.items.select_related("product_variant__product").all()
    shipping_fee = SiteSettings.get_solo().flat_shipping_fee
    subtotal = cart.subtotal
    total = (subtotal + shipping_fee) if items else 0
    return render(
        request,
        "cart/cart_detail.html",
        {
            "cart": cart,
            "items": items,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total": total,
        },
    )


@require_POST
@login_required
def add_to_cart(request):
    variant = get_object_or_404(
        ProductVariant, id=request.POST.get("variant_id"), is_active=True
    )
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    qty = max(qty, 1)

    if variant.stock_quantity < 1:
        messages.error(request, f"{variant.product.name} is out of stock.")
        return redirect(variant.product.get_absolute_url())

    cart = get_user_cart(request.user)
    existing = CartItem.objects.filter(cart=cart, product_variant=variant).first()
    current_qty = existing.quantity if existing else 0
    new_qty = current_qty + qty
    if new_qty > variant.stock_quantity:
        new_qty = variant.stock_quantity
        messages.warning(
            request, f"Only {variant.stock_quantity} of {variant.product.name} in stock."
        )
    if existing:
        existing.quantity = new_qty
        existing.save()
    else:
        CartItem.objects.create(cart=cart, product_variant=variant, quantity=new_qty)
    messages.success(request, f"Added {variant.product.name} to your cart.")
    return redirect("cart:detail")


@require_POST
@login_required
def update_item(request, item_id):
    cart = get_user_cart(request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    if qty < 1:
        item.delete()
        messages.success(request, "Item removed from cart.")
    else:
        if qty > item.product_variant.stock_quantity:
            qty = item.product_variant.stock_quantity
            messages.warning(request, "Quantity adjusted to available stock.")
        item.quantity = qty
        item.save()
    return redirect("cart:detail")


@require_POST
@login_required
def remove_item(request, item_id):
    cart = get_user_cart(request.user)
    CartItem.objects.filter(id=item_id, cart=cart).delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart:detail")
