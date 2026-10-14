# NLK interface design system

The storefront uses the supplied NLK logo, clear product information, and quiet
surfaces. Navy anchors the brand; blue identifies actions; red appears sparingly
as a brand detail. Existing Django routes, models, authentication, catalogue data,
cart calculations, payment methods, and notification integrations are retained.

## Theme and typography

Semantic RGB tokens live in `static/src/input.css` and are exposed through
`tailwind.config.js`. Use semantic utilities instead of fixed colors in templates.

| Purpose | Light value |
| --- | --- |
| Page / surface | #F6F8FC / #FFFFFF |
| Elevated surface | #EDF3FB |
| Text / secondary text | #17243A / #58677C |
| Border | #D7DFEA |
| Brand / action | #0B3278 / #1456C0 |
| Brand detail | #E5233F |
| Success / warning / error | #167548 / #925600 / #B42336 |

The `.dark` token set supplies separate text, surface, action, and status colors.
Light mode is the default; an explicit theme choice persists in local storage.
Product photography retains a white presentation surface in both themes.
Poppins is used for headings, Inter for body text, with system-font fallbacks.
Headings have compact line heights; body text uses 1.55. Form controls use at
least 16px text and a 46px minimum height; primary controls have 44px targets.

## Shared components

- `base.html`: responsive header, search, navigation, native mobile dialog, footer,
  theme control, toast region, and skip link.
- `components/icon.html`: shared decorative SVG icons, with labels on their controls.
- `components/nav_links.html`: one route list for desktop and mobile navigation.
- `components/field.html` and `form_errors.html`: labels, help, required state,
  validation messages, and error associations.
- Product card, product grid, comparison panel, Finder choices, order summary,
  and status partials preserve the app-specific data contexts.
- `.btn-*`, `.card`, `.field-*`, `.badge`, `.chip`, `.empty-state`, and status
  classes provide consistent reusable styling.

`static/src/js/site.js` manages native dialog behavior, theme persistence,
navigation state, field-error associations, variant selection, and HTMX feedback.
Filter, comparison, and Finder forms retain ordinary GET submission paths.
The mobile dialog lives outside the sticky header to avoid containing-block
conflicts; Escape and native dialog focus behavior remain available.

## Responsive behavior

Layouts use existing Tailwind breakpoints and component media queries. Product
grids increase columns as room becomes available; detail and checkout layouts
stack on small screens. Category pills and comparison tables scroll within their
own regions. Filters use an inline mobile disclosure. The mobile header retains
the logo mark and moves search to its own row. WhatsApp sits in the footer on
mobile to avoid covering form controls. Focus styles and reduced-motion rules
are included.

## Building and verification

Run `npm ci` then `npm run build:css`; generated `static/css/output.css` is ignored
by Git. The Docker Tailwind service also watches templates and builds the stylesheet.

The redesign was checked in an isolated SQLite preview with in-memory cache,
email, and task services. The core, accounts, products, cart, orders, and wholesale
suite passed 33 tests. Twelve public/authenticated pages were inspected at 320,
390, 768, 1024, and 1440px: no document-level horizontal overflow was found.
Mobile navigation, Finder selection refresh, populated comparison scrolling,
and dark mode were also inspected in the browser.

The full notification/PDF suite still requires WeasyPrint's native Windows
dependencies (GObject/Pango), which were unavailable in the local environment.
The production Docker/PostgreSQL stack was not running during final verification.
Several seeded catalogue images and contact details are placeholders; replace
these through the existing admin content tools before using demo content publicly.
