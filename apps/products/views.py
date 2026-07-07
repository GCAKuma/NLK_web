from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import AttributeValue, Category, Product, ProductQuestion


def product_list(request, category_slug=None):
    """Shop grid with search, sorting and brand/attribute faceted filtering.

    Renders just the grid partial for HTMX requests so filters apply without a
    full page reload.
    """
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
    )
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=category)

    # --- filters ---
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q)
        )

    selected_brand = request.GET.get("brand", "").strip()
    if selected_brand:
        products = products.filter(brand=selected_brand)

    selected_attrs = request.GET.getlist("attr")
    if selected_attrs:
        products = products.filter(variants__attribute_values__in=selected_attrs)

    in_stock_only = bool(request.GET.get("in_stock"))
    if in_stock_only:
        products = products.filter(
            variants__is_active=True, variants__stock_quantity__gt=0
        )

    products = products.distinct().annotate(min_price=Min("variants__price"))

    # --- sorting ---
    sort = request.GET.get("sort", "")
    if sort == "price_asc":
        products = products.order_by("min_price")
    elif sort == "price_desc":
        products = products.order_by("-min_price")
    else:
        sort = "newest"
        products = products.order_by("-created_at")

    # --- facets (scoped to the category, independent of current selection) ---
    facet_base = Product.objects.filter(is_active=True)
    if category:
        facet_base = facet_base.filter(category=category)
    brands = list(
        facet_base.exclude(brand="")
        .values_list("brand", flat=True)
        .distinct()
        .order_by("brand")
    )
    attribute_values = (
        AttributeValue.objects.filter(variants__product__in=facet_base)
        .select_related("attribute")
        .distinct()
        .order_by("attribute__name", "value")
    )

    context = {
        "products": products,
        "category": category,
        "categories": Category.objects.filter(is_active=True, parent__isnull=True),
        "product_count": products.count(),
        "brands": brands,
        "attribute_values": attribute_values,
        "q": q,
        "sort": sort,
        "selected_brand": selected_brand,
        "selected_attrs": selected_attrs,
        "in_stock_only": in_stock_only,
    }
    template = (
        "products/_product_grid.html"
        if request.htmx
        else "products/product_list.html"
    )
    return render(request, template, context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(
            "images", "specifications", "variants"
        ),
        slug=slug,
        is_active=True,
    )
    related = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)
        .select_related("category")[:4]
    )
    questions = product.questions.filter(status=ProductQuestion.Status.PUBLISHED)

    context = {
        "product": product,
        "related_products": related,
        "questions": questions,
    }
    return render(request, "products/product_detail.html", context)


def calculator_finder(request):
    """Short quiz mapping a student type to recommended calculators."""
    from .models import CalculatorRecommendation

    student_types = CalculatorRecommendation.StudentType.choices
    selected = request.GET.get("type", "")
    recommendations = []
    if selected:
        recommendations = (
            CalculatorRecommendation.objects.filter(
                student_type=selected, is_active=True
            )
            .select_related("recommended_product", "recommended_product__category")
            .prefetch_related("recommended_product__variants", "recommended_product__images")
        )

    context = {
        "student_types": student_types,
        "selected": selected,
        "recommendations": recommendations,
    }
    if request.htmx:
        return render(request, "products/_finder_result.html", context)
    return render(request, "products/calculator_finder.html", context)


def compare_calculators(request):
    """Side-by-side spec comparison via up to 3 product-picker slots.

    Each slot is a dropdown; the spec table rebuilds live over HTMX as the
    shopper changes a selection. Still accepts ?ids=1,2 for shareable links.
    """
    calc_category = Category.objects.filter(slug="calculators").first()
    calculators = Product.objects.filter(is_active=True)
    if calc_category:
        calculators = calculators.filter(category=calc_category)
    calculators = calculators.order_by("name")

    slot_names = ["p1", "p2", "p3"]
    chosen = []
    for name in slot_names:
        raw = request.GET.get(name, "")
        if raw.isdigit():
            chosen.append(int(raw))
    # Backwards-compatible with ?ids=1,2 and ?ids=1&ids=2 links
    if not chosen:
        raw_ids = []
        for raw in request.GET.getlist("ids"):
            raw_ids.extend(raw.split(","))
        chosen = [int(x) for x in raw_ids if x.strip().isdigit()]

    # De-duplicate (can't compare a product with itself) and cap at 3
    ordered, seen = [], set()
    for pid in chosen:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    ordered = ordered[:3]

    prod_map = {
        p.id: p
        for p in calculators.filter(id__in=ordered).prefetch_related("specifications")
    }
    selected = [prod_map[i] for i in ordered if i in prod_map]

    slots = [
        {"name": name, "product": selected[idx] if idx < len(selected) else None}
        for idx, name in enumerate(slot_names)
    ]

    # Aligned spec rows across the chosen products
    rows, spec_names, specs_by_product = [], [], {}
    for product in selected:
        product_specs = {}
        for spec in product.specifications.all():
            product_specs[spec.spec_name] = spec.spec_value
            if spec.spec_name not in spec_names:
                spec_names.append(spec.spec_name)
        specs_by_product[product.id] = product_specs
    for name in spec_names:
        rows.append(
            {
                "name": name,
                "values": [specs_by_product[p.id].get(name, "—") for p in selected],
            }
        )

    context = {
        "calculators": calculators,
        "slots": slots,
        "selected": selected,
        "rows": rows,
        "filled": len(selected),
    }
    template = (
        "products/_compare_panel.html" if request.htmx else "products/compare.html"
    )
    return render(request, template, context)


@require_POST
@login_required
def ask_question(request, slug):
    """Customer submits a question about a product (starts as pending)."""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    question_text = (request.POST.get("question") or "").strip()
    if question_text:
        ProductQuestion.objects.create(
            product=product,
            asked_by=request.user,
            asker_name=request.user.get_short_name(),
            question=question_text,
            status=ProductQuestion.Status.PENDING,
        )
        messages.success(
            request,
            "Thanks! Your question has been submitted and will appear once answered.",
        )
    else:
        messages.error(request, "Please enter a question.")
    return redirect("products:product_detail", slug=slug)
