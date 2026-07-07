# NLK (NugasewanaLK) — E-Commerce Platform

Single-seller Django e-commerce store for scientific calculators, educational
technology, electronics, and wholesale supply. Responsive across mobile, tablet,
and laptop, with a Daraz-style shopping experience, a midnight-navy / electric-cyan
theme, and a built-in dark mode.

## Stack

Django 5 · PostgreSQL · Django Templates + HTMX + Alpine.js + Tailwind CSS ·
Celery + Redis · WeasyPrint (invoice PDFs) · Docker Compose.
(Nginx + Gunicorn production setup is the final milestone.)

## Prerequisites

- **Docker Desktop** — the only requirement. Python, Node, Postgres and Redis
  all run in containers.

## Quick start

```bash
# 1. Env file (a working dev .env is already present)
cp .env.example .env

# 2. Build and start the full stack (web, db, redis, celery, tailwind)
docker compose up --build

# 3. In another terminal: migrate, load demo data, create an admin
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py createsuperuser
```

Then open:

- Storefront — http://localhost:8000/
- Admin — http://localhost:8000/admin/

The `tailwind` container watches templates and rebuilds `static/css/output.css`.

## Common commands

```bash
# Django
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
docker compose exec web python manage.py seed_demo          # demo catalog + content
docker compose exec web python manage.py regen_hero_images  # refresh hero art

# Frontend
docker compose exec tailwind npm run build:css              # force a CSS rebuild

# Ops
docker compose logs -f web        # tail server logs
docker compose restart web        # reload after Python changes (see Dev notes)
docker compose down               # stop everything
```

## Project structure

```
NLK web/
├── config/                     Django project package
│   ├── settings/
│   │   ├── base.py             shared settings (apps, DB, cache, email, celery)
│   │   ├── dev.py              development overrides
│   │   └── prod.py             production overrides (whitenoise, security)
│   ├── urls.py                 root URL routing
│   ├── celery.py               Celery app
│   └── wsgi.py / asgi.py       server entrypoints
│
├── apps/                       All Django apps (this dir is on the import path)
│   ├── core/                   Shared: TimeStampedModel, context processors,
│   │                           home/about/contact, mgmt commands (seed_demo, regen_hero_images)
│   ├── accounts/               Custom email User, Address, auth, profile page
│   ├── products/               Category, Product, images, specs, variants, customer Q&A,
│   │                           recommendations; catalog + product detail + finder + compare
│   ├── cart/                   Cart + CartItem, add/update/remove
│   ├── orders/                 Order, OrderItem, PaymentProof, status history, checkout
│   ├── wholesale/              QuotationRequest form + admin tracking
│   ├── content/                SiteSettings (singleton), HeroSlide, Testimonial, VideoEmbed, TrustStat
│   └── notifications/          Invoice, invoice PDF (WeasyPrint), Celery tasks, WhatsApp service
│
├── static/
│   ├── src/input.css           Tailwind source + theme tokens + components
│   └── css/output.css          compiled CSS (generated — do not edit)
├── media/                      user uploads (gitignored)
├── docs/                       project brief and design docs
│
├── Dockerfile                  Python 3.12 image (+ WeasyPrint libs)
├── docker-compose.yml          web · db · redis · celery · tailwind
├── requirements.txt            Python dependencies
├── requirements-dev.txt        dev-only extras
├── package.json                Tailwind build scripts
├── tailwind.config.js          theme tokens (dark mode: class)
├── postcss.config.js
├── manage.py
└── .env / .env.example         configuration (secrets, DB, email, WhatsApp)
```

Every app follows the same Django convention: `models.py`, `views.py`,
`urls.py`, `admin.py`, optional `forms.py`, plus `templates/`, `migrations/`,
and `tests.py`. Reusable template partials are prefixed with `_`
(e.g. `_product_card.html`, `_compare_panel.html`).

## Production

The production stack (`docker-compose.prod.yml` + `Dockerfile.prod`) runs
**Nginx → Gunicorn**, with Postgres, Redis, and a Celery worker. The image is a
multi-stage build (Node compiles minified Tailwind CSS, Python runs Gunicorn as
a non-root user); Nginx serves `/static/` and `/media/` and terminates TLS.

```bash
# 1. Create the production env file and set real secrets + domain
cp .env.prod.example .env.prod
python -c "import secrets; print(secrets.token_urlsafe(50))"   # SECRET_KEY

# 2. Build and start (migrations + collectstatic run automatically on boot)
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d

# 3. Create an admin
docker compose -f docker-compose.prod.yml --env-file .env.prod exec web \
    python manage.py createsuperuser
```

- **HTTPS** — uncomment the `443` server block in `nginx/default.conf` and the
  HTTP→HTTPS redirect, mount certs at `nginx/certs/`, and keep
  `SECURE_SSL_REDIRECT=True` / `SECURE_HSTS_SECONDS=31536000` in `.env.prod`.
- **Object storage** — set `USE_S3=True` plus the `AWS_*` vars to move media to
  S3 / Cloudflare R2 / DO Spaces (`django-storages` is installed in the prod image).
- **Hardening in place** — `DEBUG=False`, secure + HTTP-only cookies, HSTS,
  `X-Frame-Options: DENY`, nosniff, referrer-policy, `SECURE_PROXY_SSL_HEADER`.
  Verify anytime with `manage.py check --deploy`.

## Status

- **M1–M6 complete** — infra, models, admin, auth, homepage, catalog + search +
  faceted filtering, product detail with customer Q&A, cart, checkout (COD /
  bank deposit + slip upload), Celery invoice PDF + order emails + WhatsApp
  alerts, wholesale quotations, Calculator Finder, Compare tool, About/Contact.
- **UI** — semantic token theme (navy / cyan) with dark mode, profile page.
- **M7 (remaining)** — production: Nginx + Gunicorn, HTTPS, S3-ready media,
  security hardening.

## Notes

- **Theming / dark mode** — colors are semantic CSS-variable tokens in
  `static/src/input.css` (`page, surface, ink, muted, line, brand, accent, link` …)
  wired to Tailwind. Never hardcode hex in templates, or dark mode breaks. No
  gradients; cyan is used for fills/accents, a darker cyan (`link`) for text.
- **SiteSettings** is a singleton (django-solo) — set WhatsApp number, contact
  details, shipping fee, and trust stats there.
- **Product FAQs** are a per-product **customer Q&A** (`ProductQuestion`):
  customers ask, admins answer and publish.
- **Order snapshotting** — shipping address, product names and prices are copied
  onto the order at checkout so historical orders stay correct.
- **Email** goes to the console in dev; set `EMAIL_BACKEND`/SMTP in `.env` for prod.
- **WhatsApp** admin alerts use a pluggable provider (`WHATSAPP_PROVIDER=console`
  by default; `meta` for the WhatsApp Cloud API). Customer-facing buttons are
  plain `wa.me` links.

### Dev notes (Windows + Docker)

- Bind-mount file events don't always propagate, so **restart `web` after Python
  changes** (`docker compose restart web`). Templates hot-reload fine.
- The Tailwind watcher polls for changes; if styles look stale, run
  `docker compose exec tailwind npm run build:css`.
