from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("product_variant",)
    fields = ("product_variant", "quantity", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "item_count", "subtotal", "updated_at")
    search_fields = ("user__email",)
    inlines = [CartItemInline]

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.item_count

    @admin.display(description="Subtotal")
    def subtotal(self, obj):
        return f"Rs. {obj.subtotal:,.2f}"
