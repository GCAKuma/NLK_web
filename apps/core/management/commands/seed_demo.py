"""Populate the database with realistic NLK demo data.

Idempotent: safe to run multiple times. Generates simple branded placeholder
images with Pillow so the storefront looks real without uploaded media.

    docker compose run --rm web python manage.py seed_demo
"""
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from content.models import (
    HeroSlide,
    SiteSettings,
    Testimonial,
    TrustStat,
    VideoEmbed,
)
from products.models import (
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

NLK_BLUE = (10, 35, 66)
NLK_ORANGE = (255, 107, 0)
WHITE = (255, 255, 255)


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_image(text, bg=NLK_BLUE, fg=WHITE, size=(800, 800), accent=NLK_ORANGE):
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    # accent bar
    draw.rectangle([0, size[1] - 60, size[0], size[1]], fill=accent)
    font = _font(max(28, size[0] // 16))
    lines = _wrap(draw, text, font, size[0] - 120)
    line_h = font.size + 12
    total_h = line_h * len(lines)
    y = (size[1] - total_h) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((size[0] - w) / 2, y), line, font=font, fill=fg)
        y += line_h
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Seed the database with demo catalog and content."

    def handle(self, *args, **options):
        self.stdout.write("Seeding NLK demo data...")
        self._site_settings()
        categories = self._categories()
        self._products(categories)
        self._hero_slides(categories)
        self._testimonials()
        self._trust_stats()
        self._videos()
        self._recommendations()
        self.stdout.write(self.style.SUCCESS("Done. Demo data ready."))

    # ------------------------------------------------------------------ #
    def _site_settings(self):
        s = SiteSettings.get_solo()
        s.whatsapp_business_number = s.whatsapp_business_number or "94770000000"
        s.admin_notification_whatsapp_number = (
            s.admin_notification_whatsapp_number or "94770000000"
        )
        s.contact_phone = s.contact_phone or "+94 77 000 0000"
        s.contact_email = s.contact_email or "hello@nugasewana.lk"
        s.contact_address = s.contact_address or "Colombo, Sri Lanka"
        if not s.flat_shipping_fee:
            s.flat_shipping_fee = Decimal("400.00")
        s.facebook_url = s.facebook_url or "https://facebook.com/nugasewanalk"
        s.tiktok_url = s.tiktok_url or "https://tiktok.com/@nugasewanalk"
        s.follower_count = s.follower_count or "12,000+"
        s.review_count = s.review_count or "1,200+"
        s.video_view_count = s.video_view_count or "5M+"
        s.recommendation_percentage = s.recommendation_percentage or "100%"
        s.save()

    def _categories(self):
        data = [
            ("Calculators", NLK_BLUE),
            ("Computer Accessories", (18, 58, 104)),
            ("Mobile Accessories", NLK_ORANGE),
            ("Office Equipment", (13, 44, 80)),
            ("Gadgets", (230, 95, 0)),
            ("Batteries & Power", (7, 26, 50)),
        ]
        result = {}
        for order, (name, color) in enumerate(data):
            cat, _ = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "display_order": order, "is_active": True},
            )
            if not cat.image:
                cat.image.save(
                    f"{cat.slug}.jpg", make_image(name, bg=color), save=True
                )
            result[name] = cat
        return result

    def _make_product(self, category, name, brand, warranty, price, stock,
                      featured, description, specs=None, color=NLK_BLUE,
                      colors=None):
        product, _ = Product.objects.get_or_create(
            slug=slugify(name),
            defaults={
                "category": category,
                "name": name,
                "brand": brand,
                "warranty_period": warranty,
                "is_featured": featured,
                "description": description,
                "is_active": True,
            },
        )
        if not product.thumbnail:
            product.thumbnail.save(
                f"{product.slug}.jpg", make_image(name, bg=color), save=True
            )
        if not product.images.exists():
            for i in range(2):
                pi = ProductImage(
                    product=product,
                    alt_text=name,
                    display_order=i,
                    is_primary=(i == 0),
                )
                shade = color if i == 0 else NLK_ORANGE
                pi.image.save(
                    f"{product.slug}-{i}.jpg",
                    make_image(f"{name}\nView {i + 1}", bg=shade),
                    save=False,
                )
                pi.save()
        if colors:
            # Drop any earlier default variant so only the colour variants remain.
            ProductVariant.objects.filter(
                product=product, sku__endswith="-STD"
            ).delete()
            color_attr, _ = Attribute.objects.get_or_create(name="Color")
            for cname in colors:
                av, _ = AttributeValue.objects.get_or_create(
                    attribute=color_attr, value=cname
                )
                variant, _ = ProductVariant.objects.get_or_create(
                    sku=f"{product.slug[:16].upper()}-{cname[:3].upper()}",
                    defaults={
                        "product": product, "price": Decimal(price),
                        "stock_quantity": stock, "is_active": True,
                    },
                )
                VariantAttributeValue.objects.get_or_create(
                    variant=variant, attribute_value=av
                )
        else:
            ProductVariant.objects.get_or_create(
                sku=f"{product.slug[:20].upper()}-STD",
                defaults={
                    "product": product,
                    "price": Decimal(price),
                    "stock_quantity": stock,
                    "is_active": True,
                },
            )
        if specs:
            for order, (n, v) in enumerate(specs):
                ProductSpecification.objects.get_or_create(
                    product=product, spec_name=n,
                    defaults={"spec_value": v, "display_order": order},
                )
        return product

    def _products(self, cats):
        C = cats
        calc_specs = lambda funcs, disp, power, exam, dims: [
            ("Number of Functions", funcs),
            ("Display", disp),
            ("Power", power),
            ("Exam Approved", exam),
            ("Dimensions", dims),
        ]
        self.fx991es = self._make_product(
            C["Calculators"], "Casio FX-991ES Plus (2nd Edition)", "Casio",
            "1 Year", "4990", 120, True,
            "The trusted 417-function scientific calculator with Natural Textbook "
            "Display — ideal for A/L, university and professional exams.",
            calc_specs("417", "Natural Textbook (V.P.A.M.)", "Solar + Battery",
                       "Yes", "77 × 162 × 11 mm"),
            colors=["Black", "White"],
        )
        self.fx991cw = self._make_product(
            C["Calculators"], "Casio FX-991CW ClassWiz", "Casio",
            "1 Year", "6490", 80, True,
            "The next-generation ClassWiz with high-resolution display and an "
            "intuitive menu system. 540+ functions for engineering and science.",
            calc_specs("540+", "High-Resolution LCD", "Solar + Battery",
                       "Yes", "77 × 166 × 11 mm"), color=(18, 58, 104),
        )
        self._make_product(
            C["Calculators"], "Casio FX-991MS (2nd Gen)", "Casio",
            "1 Year", "3990", 90, False,
            "Classic 2-line scientific calculator with 401 functions — a reliable "
            "everyday choice for students.",
            calc_specs("401", "2-line Display", "Battery", "Yes",
                       "77 × 161 × 14 mm"), color=(13, 44, 80),
        )
        self._make_product(
            C["Calculators"], "Casio FX-82ES Plus", "Casio", "1 Year",
            "2490", 150, True,
            "Entry-level scientific calculator with Natural Display — perfect for "
            "O/L and lower-grade students.", color=(7, 26, 50),
        )
        self._make_product(
            C["Computer Accessories"], "6-in-1 USB-C Hub", "NLK", "6 Months",
            "4990", 40, True,
            "Expand your laptop with HDMI, USB 3.0, SD/microSD and USB-C power "
            "delivery in one compact hub.", color=(18, 58, 104),
        )
        self._make_product(
            C["Computer Accessories"], "Wireless Optical Mouse", "NLK",
            "1 Year", "1490", 200, False,
            "Silent-click 2.4GHz wireless mouse with adjustable DPI and long "
            "battery life.", color=(18, 58, 104),
        )
        self._make_product(
            C["Mobile Accessories"], "20W USB-C Fast Charger", "NLK",
            "1 Year", "2290", 160, False,
            "Compact 20W PD charger that fast-charges phones and tablets safely.",
            color=NLK_ORANGE,
        )
        self._make_product(
            C["Mobile Accessories"], "Braided USB-C Cable (1m)", "NLK",
            "6 Months", "890", 300, False,
            "Durable nylon-braided USB-C cable rated for fast charging and data.",
            color=NLK_ORANGE,
        )
        self._make_product(
            C["Office Equipment"], "A4 Thermal Laminator", "NLK", "1 Year",
            "8990", 25, False,
            "Fast-warm-up A4 laminator for certificates, ID cards and documents.",
            color=(13, 44, 80),
        )
        self._make_product(
            C["Gadgets"], "NLK Smart Watch", "NLK", "1 Year", "7990", 60, True,
            "Fitness and notifications smartwatch with heart-rate tracking and a "
            "bright always-on display.", color=(230, 95, 0),
            colors=["Black", "Silver"],
        )
        self._make_product(
            C["Batteries & Power"], "10000mAh Power Bank", "NLK", "1 Year",
            "3990", 100, True,
            "Slim 10000mAh power bank with dual output and USB-C input.",
            color=(7, 26, 50),
        )
        self._make_product(
            C["Batteries & Power"], "AA Rechargeable Batteries (4-pack)", "NLK",
            "6 Months", "1690", 220, False,
            "High-capacity Ni-MH rechargeable AA batteries, 4-pack.",
            color=(7, 26, 50),
        )
        self._questions()

    def _questions(self):
        qa = [
            ("Is this calculator allowed in A/L exams?",
             "Yes — the FX-991ES Plus is approved for GCE A/L examinations in Sri Lanka."),
            ("Does it come with a warranty?",
             "Yes, it includes a genuine 1-year warranty. Keep your invoice as proof of purchase."),
        ]
        for order, (q, a) in enumerate(qa):
            ProductQuestion.objects.get_or_create(
                product=self.fx991es, question=q,
                defaults={
                    "answer": a,
                    "status": ProductQuestion.Status.PUBLISHED,
                    "asker_name": "Verified Buyer",
                    "display_order": order,
                },
            )

    def _hero_slides(self, cats):
        slides = [
            ("Genuine Casio Calculators for Every Student",
             "Approved for A/L, university & professional exams",
             "417-function accuracy\nGenuine 1-year warranty\nIslandwide delivery",
             "Shop Calculators", f"/category/{cats['Calculators'].slug}/", NLK_BLUE),
            ("Wholesale & Institutional Supply",
             "Schools, universities, bookshops & tender suppliers",
             "Bulk pricing\nReliable stock\nFast quotations",
             "Request a Quotation", "/wholesale/", (18, 58, 104)),
            ("Gadgets & Accessories You Can Trust",
             "Chargers, power banks, hubs & more",
             "Quality checked\nWarranty support\nGreat prices",
             "Shop Now", "/shop/", (230, 95, 0)),
        ]
        for order, (title, sub, bullets, btn, link, color) in enumerate(slides):
            slide, _ = HeroSlide.objects.get_or_create(
                title=title,
                defaults={
                    "subtitle": sub, "bullet_points": bullets,
                    "button_text": btn, "button_link": link,
                    "display_order": order, "is_active": True,
                },
            )
            if not slide.image:
                slide.image.save(
                    f"hero-{order}.jpg",
                    make_image(title, bg=color, size=(1400, 700)), save=True,
                )

    def _testimonials(self):
        data = [
            ("Kasun Silva", "Ordered my FX-991CW and it arrived next day. Genuine product, great price!", "Facebook"),
            ("Nethmi Fernando", "Best place to buy calculators in Sri Lanka. Very helpful on WhatsApp.", "TikTok"),
            ("Ruwan Jayasuriya", "Bought calculators in bulk for our school. Smooth wholesale process.", "Facebook"),
        ]
        for order, (name, quote, source) in enumerate(data):
            Testimonial.objects.get_or_create(
                customer_name=name,
                defaults={"quote": quote, "source": source,
                          "display_order": order, "is_active": True},
            )

    def _trust_stats(self):
        stats = [
            ("Followers", "12,000+"),
            ("Recommend Us", "100%"),
            ("Content Views", "5M+"),
            ("Genuine Products", "Warranty"),
        ]
        for order, (label, value) in enumerate(stats):
            TrustStat.objects.get_or_create(
                label=label,
                defaults={"value": value, "display_order": order, "is_active": True},
            )

    def _videos(self):
        VideoEmbed.objects.get_or_create(
            embed_url_or_code="https://www.youtube.com/embed/aqz-KE-bpKQ",
            defaults={
                "platform": VideoEmbed.Platform.YOUTUBE,
                "display_order": 0, "is_active": True,
            },
        )

    def _recommendations(self):
        mapping = [
            (CalculatorRecommendation.StudentType.AL, self.fx991es),
            (CalculatorRecommendation.StudentType.ENGINEERING, self.fx991cw),
            (CalculatorRecommendation.StudentType.CA, self.fx991es),
            (CalculatorRecommendation.StudentType.UNIVERSITY, self.fx991cw),
        ]
        for order, (st, product) in enumerate(mapping):
            CalculatorRecommendation.objects.get_or_create(
                student_type=st, recommended_product=product,
                defaults={"priority": order, "is_active": True},
            )
