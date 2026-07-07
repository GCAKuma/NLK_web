from django.contrib import admin
from django.utils import timezone

from .models import (
    Attribute,
    AttributeValue,
    CalculatorRecommendation,
    Category,
    Product,
    ProductImage,
    ProductQuestion,
    ProductSpecification,
    ProductVariant,
    VariantAttributeValue,
)


# --------------------------------------------------------------------------
# Inlines
# --------------------------------------------------------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "display_order", "is_primary")


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    fields = ("spec_name", "spec_value", "display_order")


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("sku", "price", "stock_quantity", "is_active")
    show_change_link = True


class ProductQuestionInline(admin.TabularInline):
    model = ProductQuestion
    extra = 0
    fields = ("question", "answer", "status", "display_order")
    readonly_fields = ("asked_by",)


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1


class VariantAttributeValueInline(admin.TabularInline):
    model = VariantAttributeValue
    extra = 1
    autocomplete_fields = ("attribute_value",)


# --------------------------------------------------------------------------
# Model admins
# --------------------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "display_order", "is_active")
    list_filter = ("is_active", "parent")
    list_editable = ("display_order", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "brand", "display_price",
        "is_featured", "is_active", "created_at",
    )
    list_filter = ("is_active", "is_featured", "category", "brand")
    list_editable = ("is_featured", "is_active")
    search_fields = ("name", "slug", "brand")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    inlines = [
        ProductImageInline,
        ProductVariantInline,
        ProductSpecificationInline,
        ProductQuestionInline,
    ]

    @admin.display(description="From price")
    def display_price(self, obj):
        price = obj.display_price
        return f"Rs. {price:,.2f}" if price is not None else "—"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "price", "stock_quantity", "is_active")
    list_filter = ("is_active", "product__category")
    list_editable = ("price", "stock_quantity", "is_active")
    search_fields = ("sku", "product__name")
    autocomplete_fields = ("product",)
    inlines = [VariantAttributeValueInline]


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [AttributeValueInline]


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value")
    list_filter = ("attribute",)
    search_fields = ("value", "attribute__name")


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    """Customer Q&A triage queue."""

    list_display = ("product", "short_question", "asker", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("question", "answer", "product__name", "asker_name", "asked_by__email")
    autocomplete_fields = ("product",)
    readonly_fields = ("asked_by", "answered_by", "answered_at", "created_at")
    actions = ["publish_questions"]
    fields = (
        "product", "asked_by", "asker_name", "question",
        "answer", "status", "display_order",
        "answered_by", "answered_at", "created_at",
    )

    @admin.display(description="Question")
    def short_question(self, obj):
        return obj.question[:60]

    @admin.display(description="Asked by")
    def asker(self, obj):
        if obj.asked_by:
            return obj.asked_by.email
        return obj.asker_name or "—"

    def save_model(self, request, obj, form, change):
        # Stamp the answering admin when an answer is provided.
        if obj.answer and not obj.answered_by:
            obj.answered_by = request.user
            obj.answered_at = timezone.now()
            if obj.status == ProductQuestion.Status.PENDING:
                obj.status = ProductQuestion.Status.ANSWERED
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected answered questions")
    def publish_questions(self, request, queryset):
        updated = queryset.exclude(answer="").update(
            status=ProductQuestion.Status.PUBLISHED
        )
        self.message_user(request, f"{updated} question(s) published.")


@admin.register(CalculatorRecommendation)
class CalculatorRecommendationAdmin(admin.ModelAdmin):
    list_display = ("student_type", "recommended_product", "priority", "is_active")
    list_filter = ("student_type", "is_active")
    list_editable = ("priority", "is_active")
    autocomplete_fields = ("recommended_product",)
