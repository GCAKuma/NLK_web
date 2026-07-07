# Project Brief: NLK (NugasewanaLK) — E-Commerce Platform (Django)

## 1. Overview

Build a single-seller e-commerce website for **NLK (NugasewanaLK)** — "Your Trusted Choice" — Sri Lanka's online store for scientific calculators, educational technology, student essentials, electronics & gadgets, and institutional/wholesale supply.

This is a real business MVP, not a prototype. Prioritize correctness, data integrity, and a clean upgrade path over cleverness. Single seller — no multi-vendor logic, no seller dashboard; the business owner manages everything through Django admin.

## 2. Brand & Design System

**Design feel:** Modern + Premium + Trusted. Apple-style cleanliness, a Daraz-style shopping experience, with an educational focus.

**Colors:**
- Primary: Dark Blue `#0A2342`
- Secondary/accent: Orange `#FF6B00`
- Background: White
- Accent: Light Grey

**Typography:**
- Headings: Poppins Bold
- Body: Inter or Poppins Regular

Implement these as Tailwind theme tokens (custom colors + font families in `tailwind.config.js`) rather than hardcoding hex values in templates.

## 3. Project Goals & Constraints

- Real MVP launch, no fixed timeline — favor correctness and maintainability over speed.
- Single seller — no multi-vendor logic, no seller onboarding.
- **Phase 1 has no payment gateway.** Payment is Cash on Delivery or bank deposit with manual slip verification.
- Customers must create an account to purchase — no guest checkout.
- Each customer has exactly one saved address.
- Flat-rate shipping for all orders — configurable via `SiteSettings`, not a rate-calculation engine.
- Catalog is scoped to: Calculators, Computer Accessories, Mobile Accessories, Office Equipment, Gadgets, Batteries & Power (matching the "Shop by Category" section below) — not a general/broad marketplace catalog.
- Reviews/ratings (as a rating system), flash sales, coupons, dealer registration, and a blog (Student Corner) are Phase 2 — see Section 8.

## 4. Tech Stack

| Layer | Choice |
|---|---|
| Backend framework | Django (latest stable) |
| Database | PostgreSQL |
| Frontend | Django Templates + HTMX + Alpine.js + Tailwind CSS |
| Async task queue | Celery |
| Cache / message broker | Redis |
| PDF generation | WeasyPrint (invoices) |
| Email | Django's email backend (SMTP; swappable for SendGrid later) |
| WhatsApp (admin order alerts) | Pluggable service class/interface, provider configured via settings |
| WhatsApp (customer-facing buttons) | Simple `wa.me` deep links — no API/backend needed |
| File storage | Local filesystem for MVP; structured for an easy swap to S3/R2 via `django-storages` later |
| Containerization | Docker + docker-compose (web, db, redis, celery worker) |
| Production web server | Gunicorn behind Nginx |
| Admin interface | Customized Django admin — no separate custom dashboard |

## 5. System Architecture

Request flow: **Client browser → Nginx → Gunicorn → Django application**, reading/writing PostgreSQL directly, using Redis for caching and as the Celery broker. Invoice generation, email sending, and admin WhatsApp alerts are dispatched as **Celery tasks**, never run synchronously in the request cycle.

Order placement flow:
1. Checkout creates `Order` + `OrderItem`s with status `pending`.
2. Bank deposit → customer uploads a slip → `PaymentProof` created → status `payment_verification`. COD orders can move straight to `confirmed`.
3. Celery task: generate invoice PDF → email to admin + customer → WhatsApp alert to admin.
4. Customer sees an immediate confirmation page, not blocked on step 3.
5. Admin reviews/approves the slip in Django admin, updates status; every change is logged in `OrderStatusHistory`.

## 6. Site Structure & Page Requirements

### 6.1 Navigation Menu
Home / Shop / Calculators / Wholesale / Student Corner (Phase 2 placeholder link, can 404 or "coming soon" until built) / About Us / Contact

### 6.2 Homepage Sections
1. **Hero banner** — rotating slides, each with a headline, supporting bullet points, and a CTA button (e.g. "Shop Now"). Implement as a simple `HeroSlide` model (title, subtitle, bullet points, image, button text, button link, display order, is_active) so the admin can manage slides without code changes.
2. **Trust section** — static/admin-editable stats (follower count, review count, video views, recommendation %, warranty info). Store these as fields on `SiteSettings` or a small `TrustStat` model (label, value, display_order).
3. **Shop by category** — cards linking to: Calculators, Computer Accessories, Mobile Accessories, Office Equipment, Gadgets, Batteries & Power. Maps directly to top-level `Category` records.
4. **Best sellers** — product cards showing image, price, warranty info, a WhatsApp order button, and an Add to Cart button. "Best seller" can be a manually curated flag on `Product` (`is_featured` boolean) for MVP rather than computed sales ranking.
5. **Why choose NLK** — static icon + text list (genuine products, competitive prices, warranty support, fast delivery, trusted by students). Can be a simple template partial; doesn't need a DB model unless the client wants to edit it without a deploy.
6. **Student Corner preview** — Phase 2 (blog not built yet); omit this section or show a "coming soon" placeholder for MVP.
7. **Customer reviews** — curated testimonials/screenshots. Model as `Testimonial` (customer name, quote or screenshot image, source e.g. "Facebook", display_order, is_active). This is curated social proof, distinct from a product rating/review system (which remains Phase 2).
8. **Video showcase** — embedded Facebook/TikTok/YouTube/Reels content. Model as `VideoEmbed` (platform, embed_url_or_code, thumbnail, display_order, is_active).
9. **Wholesale solutions** — description of wholesale/institutional supply (schools, universities, bookshops, tender suppliers) with a "Request Quotation" button linking to the quotation request form (Section 7.1).
10. **Contact** — WhatsApp, Messenger, phone, email, and location. Pull all of these from `SiteSettings` so they're editable in one place.

### 6.3 Product Page
Large product image (gallery), price, warranty info, description, features, FAQ, WhatsApp order button, Add to Cart button, related products.

- FAQ can be a simple `ProductFAQ` model (product FK, question, answer, display_order) or a shared FAQ if most questions are generic — confirm with the business if FAQs are per-product or store-wide before building.
- Warranty info: add a `warranty_period` field (e.g. "1 Year") to `Product`.
- The WhatsApp order button generates a `wa.me` link pre-filled with the product name and a request-to-order message.

### 6.4 About Us Page
Static content page using the copy provided:

> NLK (NugasewanaLK) is a trusted supplier of scientific calculators and educational technology solutions in Sri Lanka. With over 12,000 followers, 100% customer recommendations, and millions of content views, NLK serves students, professionals, educational institutions, and businesses with genuine products, competitive prices, and reliable warranty support.

Implement as a simple template or a `FlatPage`-style model if the client wants to edit this copy without a code deploy.

## 7. New Functional Requirements (Beyond Core Storefront)

### 7.1 Wholesale Quotation Request (MVP)
A form (not a cart purchase) capturing: contact name, organization name, organization type (school / bookshop / government institution / university / other), email, phone, requested items or requirements (free text), and optionally a reference to specific products. Store as `QuotationRequest` with a status field (new / contacted / quoted / closed) so the admin can track follow-up in Django admin. Trigger an email/WhatsApp alert to admin on submission (reuse the same Celery notification pattern as orders).

### 7.2 Calculator Finder (MVP)
A short quiz: "Are you an A/L Student / Engineering Student / CA Student / University Student?" → recommends a calculator. Implement via a `CalculatorRecommendation` model (student_type choice field, recommended `Product` FK, priority/display order) so the mapping is admin-editable, not hardcoded. The quiz UI itself can be a simple Alpine.js-driven form with no page reload, hitting a small Django view that returns the recommended product(s).

### 7.3 Compare Calculators (MVP)
Side-by-side comparison of 2-3 products' specs (e.g. FX-991MS vs FX-991ES Plus vs FX-991CW). Requires a `ProductSpecification` model (product FK, spec_name, spec_value, display_order) so any product can expose structured specs, and the comparison view renders a table aligning shared spec names across the selected products.

### 7.4 WhatsApp Integration (MVP)
- **Floating WhatsApp button**: sitewide, always visible, links to the business WhatsApp number (from `SiteSettings`).
- **Per-product WhatsApp order button**: pre-fills a message with the product name/link.
- These are independent of the Celery-based admin order-alert system described in Section 5 — they're customer-initiated outbound links, not backend notifications.

### 7.5 Deferred to Phase 2 (do not build now)
- **Dealer Registration** — a distinct account type/flow for wholesale dealers.
- **Student Corner (blog)** — articles like "Best Calculator for A/L Maths," "FX-991CW Guide," etc. This needs its own content model (`Article`: title, slug, content, cover image, published_at, is_published) and a listing/detail view — worth its own scoping pass when prioritized.

## 8. Explicitly Out of Scope for This Phase

- Multi-vendor / multiple sellers.
- Payment gateway integration (e.g. PayHere) — don't design in a way that blocks adding this later.
- Product rating/review system (distinct from the curated `Testimonial` model in 6.2, which *is* in scope).
- Flash sales / time-limited deals.
- Coupons / discount codes.
- Wishlist.
- Multiple saved addresses per user.
- Dealer registration (Section 7.5).
- Student Corner / blog (Section 7.5).
- Shipping cost calculation based on weight/distance (flat rate only).

## 9. Database Schema

Implement the following models (add `created_at`/`updated_at` timestamps where sensible even if not explicitly listed):

**User** (custom user model) — `id`, `email` (unique, login field), `phone_number`, `is_staff`, `is_active`, `date_joined`

**Address** — `id`, `user` (OneToOneField), `full_name`, `phone_number`, `address_line1`, `address_line2` (optional), `city`, `district`, `postal_code`, `updated_at`

**Category** — `id`, `parent` (FK to self, nullable), `name`, `slug`, `image`, `is_active`

**Product** — `id`, `category` (FK), `name`, `slug`, `description`, `brand` (optional), `thumbnail`, `warranty_period` (e.g. "1 Year"), `is_featured` (bool, for "Best Sellers"), `is_active`, `created_at`, `updated_at`

**ProductImage** — `id`, `product` (FK), `image`, `alt_text`, `display_order`, `is_primary`

**ProductSpecification** — `id`, `product` (FK), `spec_name`, `spec_value`, `display_order`

**ProductFAQ** — `id`, `product` (FK), `question`, `answer`, `display_order` *(confirm with business whether FAQs are per-product or store-wide before building)*

**Attribute** — `id`, `name` (e.g. "Color", "Size")

**AttributeValue** — `id`, `attribute` (FK), `value`

**ProductVariant** — `id`, `product` (FK), `sku` (unique), `price`, `stock_quantity`, `is_active`, `created_at`

**VariantAttributeValue** (join table) — `variant` (FK), `attribute_value` (FK)

**Cart** — `id`, `user` (OneToOneField), `created_at`, `updated_at`

**CartItem** — `id`, `cart` (FK), `product_variant` (FK), `quantity`, `added_at` — unique together on (cart, product_variant)

**Order** — `id`, `user` (FK), `order_number` (unique), `status` (pending / payment_verification / confirmed / shipped / delivered / cancelled), `payment_method` (cod / bank_deposit), `shipping_full_name`, `shipping_phone`, `shipping_address_line1`, `shipping_address_line2`, `shipping_city`, `shipping_district`, `shipping_postal_code`, `subtotal`, `shipping_fee`, `total`, `customer_notes` (optional), `created_at`, `updated_at`

*(Shipping fields are a snapshot copied at checkout time — do not just reference `Address` by FK, since the user's saved address may change later.)*

**OrderItem** — `id`, `order` (FK), `product_variant` (FK), `product_name_snapshot`, `variant_label_snapshot`, `unit_price`, `quantity`, `line_total`

**PaymentProof** — `id`, `order` (OneToOneField), `slip_image`, `uploaded_at`, `status` (pending / verified / rejected), `verified_by` (FK to User, nullable), `verified_at`, `admin_notes`

**Invoice** — `id`, `order` (OneToOneField), `invoice_number` (unique), `pdf_file`, `generated_at`, `emailed_at`

**OrderStatusHistory** — `id`, `order` (FK), `status`, `changed_by` (FK to User, nullable), `changed_at`, `note`

**QuotationRequest** — `id`, `contact_name`, `organization_name`, `organization_type` (school / bookshop / government / university / other), `email`, `phone`, `requirements` (text), `status` (new / contacted / quoted / closed), `created_at`

**CalculatorRecommendation** — `id`, `student_type` (A/L / Engineering / CA / University), `recommended_product` (FK to Product), `priority`, `is_active`

**HeroSlide** — `id`, `title`, `subtitle`, `bullet_points` (text or small related model), `image`, `button_text`, `button_link`, `display_order`, `is_active`

**Testimonial** — `id`, `customer_name`, `quote` (optional), `screenshot_image` (optional), `source` (e.g. "Facebook"), `display_order`, `is_active`

**VideoEmbed** — `id`, `platform` (Facebook / TikTok / YouTube / Reels), `embed_url_or_code`, `thumbnail`, `display_order`, `is_active`

**SiteSettings** (singleton — enforce single row at the application level) — `whatsapp_business_number`, `admin_notification_whatsapp_number`, `contact_phone`, `contact_email`, `contact_address`, `flat_shipping_fee`, `social_links` (JSON or separate fields), `follower_count`, `review_count`, `video_view_count`, `recommendation_percentage`

## 10. Suggested Django App Structure

```
accounts/        - Custom User, Address
products/        - Category, Product, ProductImage, ProductSpecification, ProductFAQ,
                   Attribute, AttributeValue, ProductVariant, VariantAttributeValue,
                   CalculatorRecommendation
cart/            - Cart, CartItem
orders/          - Order, OrderItem, PaymentProof, OrderStatusHistory
wholesale/       - QuotationRequest
content/         - HeroSlide, Testimonial, VideoEmbed, SiteSettings
notifications/   - Invoice model + Celery tasks (PDF generation, email, WhatsApp)
core/            - Shared base templates, utilities
```

## 11. Suggested Build Order

1. Docker Compose setup (Django, Postgres, Redis, Celery worker).
2. Custom User + Address models; registration/login.
3. Tailwind theme setup with NLK's brand colors/fonts.
4. Category, Product (+ specs, FAQ, images), ProductVariant, Attribute/AttributeValue + admin customization.
5. Homepage build: HeroSlide, SiteSettings-driven trust stats, category cards, best sellers, why-choose-us, Testimonial, VideoEmbed sections.
6. Public storefront: category pages with attribute filtering, product detail pages (incl. WhatsApp order button).
7. Cart (DB-backed) and checkout flow (address confirmation, payment method, slip upload).
8. Celery tasks: invoice PDF, email, admin WhatsApp alert.
9. Admin workflows: payment verification, order status + history.
10. Wholesale quotation request form + admin tracking.
11. Calculator Finder quiz (Alpine.js UI + `CalculatorRecommendation` lookup).
12. Compare Calculators tool (spec table from `ProductSpecification`).
13. Floating WhatsApp button + Contact page wired to `SiteSettings`.
14. About Us static page.
15. Nginx + Gunicorn production config, HTTPS.

## 12. Implementation Notes for the Coding Agent

- Favor Django conventions (class-based views, Django admin, Django forms) over custom-rolled solutions.
- Use environment variables for all secrets and environment-specific config.
- Enforce model-level constraints (non-negative stock/prices, `unique_together`) rather than relying solely on form validation.
- Keep WhatsApp admin-notification logic behind a swappable service class; the customer-facing WhatsApp buttons are plain `wa.me` links and need no such abstraction.
- All Celery tasks should be idempotent and retry on transient failure.
- Follow the snapshotting pattern in Section 9 consistently for anything order-related.
- Enforce `SiteSettings` as a true singleton (e.g. override `save()` to always use pk=1, or use a package like `django-solo`).
- Confirm with the business whether `ProductFAQ` should be per-product or store-wide before implementing Section 6.3's FAQ section.
