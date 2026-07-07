from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify

from core.models import TimeStampedModel


class Category(TimeStampedModel):
    """Top-level and nested product categories (e.g. Calculators)."""

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_top_level(self):
        return self.parent_id is None


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100, blank=True)
    thumbnail = models.ImageField(upload_to="products/", blank=True)
    warranty_period = models.CharField(
        max_length=50, blank=True, help_text='e.g. "1 Year"'
    )
    is_featured = models.BooleanField(
        default=False, help_text="Show in the Best Sellers section."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:product_detail", kwargs={"slug": self.slug})

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first() or self.images.first()
        if img:
            return img.image
        return self.thumbnail or None

    @property
    def default_variant(self):
        return self.variants.filter(is_active=True).order_by("price").first()

    @property
    def display_price(self):
        variant = self.default_variant
        return variant.price if variant else None

    @property
    def in_stock(self):
        return self.variants.filter(is_active=True, stock_quantity__gt=0).exists()


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "display_order", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductSpecification(models.Model):
    """Structured spec rows, used on the product page and the Compare tool."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="specifications"
    )
    spec_name = models.CharField(max_length=120)
    spec_value = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.spec_name}: {self.spec_value}"


class ProductQuestion(TimeStampedModel):
    """Customer question + admin answer, shown on the product page once published."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ANSWERED = "answered", "Answered (draft)"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="questions"
    )
    asked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_questions",
    )
    asker_name = models.CharField(
        max_length=120, blank=True, help_text="Display name if the asker is anonymous."
    )
    question = models.TextField()
    answer = models.TextField(blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="answered_questions",
    )
    answered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"Q on {self.product.name}: {self.question[:50]}"

    @property
    def is_public(self):
        return self.status == self.Status.PUBLISHED and bool(self.answer)


class Attribute(models.Model):
    """A variant dimension, e.g. Color or Size."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=120)

    class Meta:
        ordering = ["attribute__name", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "value"], name="uniq_attribute_value"
            )
        ]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(TimeStampedModel):
    """A sellable SKU of a product with its own price and stock."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    attribute_values = models.ManyToManyField(
        AttributeValue,
        through="VariantAttributeValue",
        related_name="variants",
        blank=True,
    )

    class Meta:
        ordering = ["price"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0), name="variant_price_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="variant_stock_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} [{self.sku}]"

    @property
    def label(self):
        values = self.attribute_values.all()
        if values:
            return " / ".join(av.value for av in values)
        return "Default"

    @property
    def in_stock(self):
        return self.is_active and self.stock_quantity > 0


class VariantAttributeValue(models.Model):
    """Join row linking a variant to one attribute value."""

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="variant_attribute_values",
    )
    attribute_value = models.ForeignKey(
        AttributeValue, on_delete=models.CASCADE, related_name="variant_links"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "attribute_value"],
                name="uniq_variant_attribute_value",
            )
        ]

    def __str__(self):
        return f"{self.variant.sku} → {self.attribute_value}"


class CalculatorRecommendation(TimeStampedModel):
    """Maps a student type to a recommended product (Calculator Finder quiz)."""

    class StudentType(models.TextChoices):
        AL = "al", "A/L Student"
        ENGINEERING = "engineering", "Engineering Student"
        CA = "ca", "CA Student"
        UNIVERSITY = "university", "University Student"

    student_type = models.CharField(max_length=20, choices=StudentType.choices)
    recommended_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="recommendations"
    )
    priority = models.PositiveIntegerField(
        default=0, help_text="Lower number shows first."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["student_type", "priority"]

    def __str__(self):
        return f"{self.get_student_type_display()} → {self.recommended_product.name}"
