# Sankofa Library System

A web-based academic library management application built with **Flask**, **SQLAlchemy**, **Jinja2**, and a warm Afrocentric design system. Originally adapted from the original Flask project ([Des-s/Sankofa-Library-System](https://github.com/Des-s/Sankofa-Library-System)) and faithfully re-aligned with the design language, security posture, and feature set of the Next.js rewrite (`/home/z/my-project`).

> "Sankofa" is an Akan word meaning *"go back and fetch it"* — the wisdom of learning from the past as you move forward. This project digitises academic library operations for the whole campus: catalog search, physical borrowing, online reading, fines, and audit-grade reporting.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Demo Credentials](#demo-credentials)
3. [Design System](#design-system)
4. [Security Features](#security-features)
5. [Features by Role](#features-by-role)
6. [New Features](#new-features)
7. [Bug Fixes Applied](#bug-fixes-applied)
8. [Architecture](#architecture)
9. [Database Schema](#database-schema)
10. [Background Scheduler](#background-scheduler)
11. [Environment Variables](#environment-variables)
12. [Comparison with Next.js Version](#comparison-with-nextjs-version)
13. [Auth Differences](#auth-differences-flask-server-sessions-vs-nextjs-jwt-triple-channel)
14. [Tooltips and Confirmation Dialogs](#tooltips-and-confirmation-dialogs)

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

By default the app uses SQLite for local development. For MySQL:

```
DATABASE_URL=mysql+pymysql://user:password@localhost/sankofa_library
```

```sql
CREATE DATABASE sankofa_library CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Seed sample data

```bash
python seed.py
```

### 4. Run

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000). The app is a **standalone Flask service on port 5000**.

### 5. Verify

```bash
python -c "from app import create_app; app = create_app(); print('OK')"
# → prints "OK" (a RuntimeWarning will fire if SECRET_KEY is still the dev default — that's intentional)
```

---

## Demo Credentials

Seeded by `seed.py`:

| Role      | Email                       | Password       |
|-----------|-----------------------------|----------------|
| Admin     | `admin@sankofa.edu`         | `admin12345`   |
| Librarian | `librarian@sankofa.edu`     | `librarian123` |
| Student   | `student1@sankofa.edu`      | `student123`   |
| Student   | `student2@sankofa.edu`      | `student123`   |
| Student   | `student3@sankofa.edu`      | `student123`   |

> The login page deliberately **does not** print these credentials — they are documented here and in `README.md`. Removing the hardcoded demo-credential table from `login.html` was a deliberate security improvement (FLASK-ADAPT).

Library cards are issued during seeding (format: `LIB-2026-STU2024001`).

---

## Design System

The Flask version faithfully ports the Next.js design tokens defined in `src/app/globals.css`. All design decisions live in `app/static/css/style.css`.

### Color palette

| Token              | Value       | Usage                                    |
|--------------------|-------------|------------------------------------------|
| `--forest`         | `#1B4332`   | Primary brand — deep forest green        |
| `--forest-light`   | `#2D6A4F`   | Secondary green                          |
| `--gold`           | `#B8860B`   | Warm gold accent                         |
| `--gold-light`     | `#D4A574`   | Light gold accent                        |
| `--kente`          | `#C04E2C`   | Kente orange                             |
| `--adinkra`        | `#8B1A1A`   | Adinkra red                              |
| `--color-bg`       | `#FDF8F0`   | Warm off-white background                |
| `--color-text`     | `#2C1810`   | Warm dark brown foreground               |
| `--color-muted`    | `#6B5B4E`   | Muted text                               |
| `--color-border`   | `#E5DFD3`   | Surface border                           |
| `--color-surface`  | `#FFFFFF`   | Cards / surfaces                         |
| `--color-danger`   | `#B91C1C`   | Destructive actions                      |
| `--success`        | `#15803D`   | Success states                           |

### Dark mode

`[data-theme="dark"]` overrides:

| Token             | Value       |
|-------------------|-------------|
| `--color-bg`      | `#161210`   |
| `--color-surface` | `#221C18`   |
| `--color-text`    | `#F5EDE3`   |
| `--color-border`  | `#3A2F26`   |

Dark mode is per-user (`User.theme_preference`) and toggled from **Settings → Appearance**.

### Fonts

Google Fonts loaded via `<link>` in `base.html` and via `@import` in `style.css`:

- **Outfit** — headings (h1-h6, .font-heading)
- **Inter** — body text (default sans)

### Signature gradients & utility classes

| Class                       | Description                                                                 |
|-----------------------------|-----------------------------------------------------------------------------|
| `.kente-bar`                | Repeating-linear-gradient stripe (forest / gold / kente / adinkra)          |
| `.library-card-visual`      | Radial + linear gradient for student library cards                          |
| `.gradient-sankofa`         | Forest → forest-light → gold linear gradient (background)                   |
| `.gradient-sankofa-text`    | Same gradient clipped to text (`-webkit-text-fill-color: transparent`)      |
| `.gradient-gold`            | Gold-light → gold → kente linear gradient                                   |
| `.gradient-gold-text`       | Same gradient clipped to text                                               |
| `.gradient-kente`           | Forest → kente → gold linear gradient                                       |
| `.btn-gradient`             | Animated gradient button with shimmer sweep on hover (`!important` bg)      |
| `.btn-gradient-gold`        | Gold variant of the gradient button                                         |
| `.lift-on-hover`            | `translateY(-2px)` + larger shadow on hover                                 |
| `.fancy-scroll`             | Thin custom scrollbar (8px)                                                 |
| `.skeleton-shimmer`         | Loading placeholder with `shimmer` keyframe                                 |
| `.empty-state-component`    | Centered empty-state block (icon + heading + body)                          |
| `.table-container`          | Responsive table wrapper with horizontal scroll on small screens            |

### Animations

Keyframes: `fade-in-up`, `fade-in-down`, `scale-in`, `float`, `pulse-soft`, `gradient-shift`, `shimmer`.

Utility classes: `.animate-fade-in-up`, `.animate-fade-in-down`, `.animate-float`, `.animate-pulse-soft`, `.animate-scale-in`. Stagger helpers `.stagger-1` … `.stagger-6`.

### Reduced motion & print

```css
@media (prefers-reduced-motion: reduce) { /* disable animations */ }
@media print { /* hide .no-print, force black-on-white */ }
```

A `.no-print` class hides nav, toasts, breadcrumbs, and footer when printing.

---

## Security Features

The Flask version is **not** a toy demo — it ships the same hardening as the Next.js version.

### Rate limiting & account lockout

- 5 failed login attempts on a single account → 15-minute lockout (configurable via `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES`).
- Lockout is enforced *before* the password check, so timing attacks can't distinguish "locked" from "wrong password".
- Successful login resets `failed_login_attempts` to 0 and clears `locked_until`.
- `User.failed_login_attempts`, `User.locked_until`, `User.last_login_at` are persisted columns (FLASK-ADAPT).
- `Flask-Limiter` is included in `requirements.txt` for additional HTTP-level rate limiting.

### Forgot password

- Generates a **20-character** temp password via `secrets.choice()` (≥16 required by spec).
- Temp password is **never displayed on screen** — only sent via email (or logged if mail is suppressed).
- `must_change_password=True` is set after reset so the user is nudged to rotate it.
- Generic flash message: *"If that email is registered, a temporary password has been sent to it."* — no information disclosure on whether the email exists.

### Logout is POST-only with CSRF

- `@auth_bp.route('/logout', methods=['POST'])` — GET returns 405.
- The header logout button is now a `<form method="POST">` with a hidden `csrf_token` field (CSRF protection is global via Flask-WTF).

### File upload validation (`app/utils/helpers.py`)

- `validate_image_upload()`: extension allowlist (`jpg`/`jpeg`/`png`) + magic-byte verification (`FF D8 FF` for JPEG, `89 50 4E 47` for PNG) + MIME-type sniff.
- `validate_book_file_upload()`: extension allowlist (`pdf`/`txt`/`html`/`htm`) + non-empty check.
- Both helpers **fix the `IndexError` when a file has no extension** — they return `(False, "File has no extension.")` instead of crashing.
- `generate_library_card_number()` is wrapped in `try/except` with a fallback to `LIB-{year}-{student_id}` so a malformed admin setting never blocks registration.

### Cover fetcher hardening (`app/utils/covers.py`)

- Uses `requests` with a **10s timeout**.
- Validates `Content-Type` starts with `image/*` before saving.
- Streams the response with a hard **5 MB cap** — aborts if the body exceeds it.
- Catches specific exceptions: `Timeout`, `HTTPError`, `ConnectionError`, `RequestException`, `OSError`.

### Session security (`app/config.py`)

- `SESSION_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`
- `SESSION_COOKIE_SECURE` toggled by env var (true in production)
- `SESSION_PERMANENT = True` with **8-hour** `PERMANENT_SESSION_LIFETIME`
- `SECRET_KEY` is validated at startup — a `RuntimeWarning` is emitted if the default value is still in use.

### Security headers (`app/__init__.py`)

Applied via `@app.after_request` on every response:

- `Content-Security-Policy` — restrictive `default-src 'self'`, `object-src 'none'`, `frame-ancestors 'self'`, with CDN allowlists for the CDN-hosted Font Awesome / Chart.js / Google Fonts.
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### CSRF

Global CSRF protection via Flask-WTF (`CSRFProtect`) on every POST/PUT/DELETE form. All inline icon-only POST buttons (logout, approve, reject, deactivate, mark-paid, waive) include a hidden `csrf_token` field.

### Audit logging

`AuditLog` records every meaningful action (`LOGIN`, `LOGOUT`, `LOGIN_FAILED`, `ACCOUNT_LOCKED`, `REGISTER`, `PASSWORD_RESET`, `PASSWORD_CHANGE`, `CHECKOUT`, `RETURN`, `FINE_PAID`, `FINE_WAIVED`, `BOOK_CREATE`, `BOOK_UPDATE`, `BOOK_DEACTIVATE`, `STUDENT_APPROVE`, `STUDENT_REJECT`, `STUDENT_EDIT`, `USER_CREATE`, `USER_UPDATE`, `USER_TOGGLE`, `SETTINGS_UPDATE`, `SUPPORT_REQUEST`, `REPORT_FILED`, `DUE_SOON_REMINDERS`, `OVERDUE_DIGEST`, `ACCESS_DENIED`). Searchable and filterable from `/admin/audit`.

---

## Features by Role

### Student (`/student/*`)

- Self-registration with student email domain enforcement (`st.knust.edu.gh` by default; configurable in Settings).
- Dashboard: library card visual, active checkouts, outstanding fines, recent reading sessions.
- Catalog browsing with search, category/subcategory filter, availability filter.
- Book detail page with full metadata, availability, cover, and **related books by category** (FLASK-ADAPT).
- Online reading of digital titles with library-card verification.
- Borrowings history (active + returned).
- Fines list.
- Profile (change password, upload photo).
- Settings (notifications, theme, language, support request).

### Librarian (`/librarian/*`) — also accessible to admins

- Dashboard: today's checkouts, overdues, active loans, recent activity.
- **Approvals page** (`/librarian/approvals`) — dedicated pending-approvals review screen with Approve/Reject buttons + confirmation dialogs (FLASK-ADAPT).
- Student lookup with pending-approvals tab.
- Checkout workflow (search student → pick book → due-date computed from `loan_period_days`).
- Return workflow (with auto-fine calculation).
- Overdue list with accrued-fine preview.
- Fines management (mark paid / waive with reason).
- Book CRUD with cover-image validation + auto-fetch by ISBN.
- Reports (file lost/damaged, student incidents, inventory issues).
- Analytics (department breakdown, availability rate, on-time return rate, digital coverage).
- Profile + settings.

### Admin (`/admin/*`)

- **Dashboard with three Chart.js charts** (FLASK-ADAPT):
  - User growth (line, last 6 months)
  - Checkout volume (bar, last 6 months)
  - Books by category (doughnut)
  - Plus department pie chart and four ring-style KPI cards (availability, on-time returns, digital coverage, fine collection).
  - All numbers are **real DB-driven** — no hardcoded marketing figures.
- User management (list, add, edit, toggle active, view detail).
- **System settings** (`/admin/settings`) — fine_rate_per_day, loan_period_days, library_card_format, max_active_checkouts, **student_email_domain**, **currency_symbol**, library_name, library_address (FLASK-ADAPT).
- **Audit log** (`/admin/audit`) — searchable, filterable by action_type and target_table (FLASK-ADAPT).
- Reports.
- Profile + settings.

---

## New Features

These were added in the FLASK-ADAPT pass:

1. **Student Approval Workflow** — `/librarian/approvals` route + `librarian/approvals.html` template. Lists pending students as cards with avatar, metadata, Approve/Reject/View buttons. Approve/Reject buttons open a JS `confirm()` dialog. Every action logs `STUDENT_APPROVE` / `STUDENT_REJECT` to the audit trail.

2. **Book Detail Page** — `/catalog/<int:book_id>` route + rewritten `catalog/detail.html`. Two-column layout with cover, quick actions (Read Online for students), availability card (physical + digital), bibliographic details grid, and a "More from {category}" related-books rail.

3. **Admin Audit Log** — `/admin/audit` route + rewritten `admin/audit.html`. Filter by `q` (free text), `action_type` (dropdown of distinct values), and `target_table` (dropdown of distinct values). Paginated at 50/page. Sticky header table inside a `.table-container` for horizontal scroll on small screens.

4. **Admin System Settings** — extended `SystemSettingsForm` with `student_email_domain`, `currency_symbol`, `library_name`, `library_address`. The settings page now writes new rows to `SystemSetting` if they don't exist (not just updates existing). All defaults seeded by `init_default_settings()` on first boot.

5. **Admin Dashboard Charts** — three Chart.js charts (user growth line, checkout volume bar, category distribution doughnut). All data sourced from real DB queries via `_get_checkout_volume_by_month()` and `_get_category_distribution()` helpers. Theme-aware palette aligned with the Sankofa design system.

---

## Bug Fixes Applied

1. **Real DB stats on the landing page** — `auth.index()` returns `book_count`, `student_count`, `category_count` from the database; `index.html` renders them with `{{ book_count }}+` instead of hardcoded `10,000+` / `5,000+`.

2. **Contact form action** — `resources.html` posts to `{{ url_for('auth.contact') }}` with a CSRF token; the route handles GET (redirect to anchor) and POST (send mail + flash).

3. **Stale fines** (`app/utils/fines.py`) — `update_overdue_statuses()` now also iterates every `Fine` tied to an active/overdue `Checkout` and refreshes `days_overdue` and `total_amount` to the current date. The hourly scheduler keeps fine totals accurate without a manual return.

4. **Double-return guard** (`app/utils/fines.py`) — `process_return()` early-returns `None` if `checkout.status == 'returned'` or `actual_return_date` is set; only increments `book.available_physical_copies` when `book.available_physical_copies < book.total_physical_copies` so a double-return can't inflate the shelf count past the cap.

5. **Notification resilience** (`app/utils/notifications.py`) — every `mail.send()` is wrapped in `_safe_send()` which catches `SMTPException` + `OSError` and logs via `app.logger.error()`. `print()` statements replaced with `app.logger.info()` / `app.logger.error()`. Orphaned checkouts (missing student or book) are skipped with a warning, never raise.

6. **`IndexError` on extension-less uploads** — `validate_image_upload()` and `validate_book_file_upload()` return `(False, "File has no extension.")` instead of crashing.

7. **`generate_library_card_number()` malformed-format safety** — wrapped in `try/except (KeyError, ValueError, IndexError)` with a fallback.

8. **Scroll-linked theme transition (laser beam + particles + progress)** — the homepage bottom half is wrapped in a `.dark-zone` div. As the user scrolls, an enhanced physics-driven laser beam (damped spring simulation, 60fps `requestAnimationFrame`) sweeps down the page with:
   - **Glowing particle embers** that spawn along the beam and drift upward (max 30 particles, 1-2s life)
   - **Side progress rail** on the right edge showing scroll progress (0-100%) with a glowing dot
   - **Velocity-based beam tilt** (±4 degrees based on beam velocity)
   - **Content reveal** — sections with `.beam-reveal` fade in when the beam passes
   - **Beam shimmer** — a bright highlight travels along the beam every 2.5s
   - **Bright core line** — a thinner white line inside the beam
   - **Elastic collision boundary** — beam bounces off the light-zone boundary with 65% energy retention
   - **Bounce margin** — beam can penetrate 15px into the light zone before hard clamp
   - **Scroll momentum coupling** — flicking the scrollwheel launches the beam
   - **Force-reveal fallback** — when progress >= 1, all `.beam-reveal` sections are force-revealed (prevents stuck at opacity 0)
   - Respects `prefers-reduced-motion: reduce` (all effects hidden)
   - **Physics parameters**: STIFFNESS=0.15, DAMPING=0.12 (underdamped, critical ratio 0.155), BOUNCE_RESTITUTION=0.65, MAX_VELOCITY=40, Velocity-Verlet integration
   See `app/templates/base.html` (physics JS) and `app/static/css/style.css` (CSS classes).

### Homepage Sections

The homepage includes the following sections, all within the dark zone (laser beam transition):

| Section | ID | Description |
|---------|-----|-------------|
| Hero | — | Library background image, gradient headline, floating library card visual |
| Stats Band | `#stats` | Real DB-driven counts (books, copies, students, categories) |
| Features | `#features` | 6 feature cards with icons and hover effects |
| How It Works | `#how-it-works` | 3-step getting started guide |
| Featured Books | `#featured` | Recently added books from the catalogue |
| Testimonials | `#testimonials` | Community quotes from librarian and student |
| **News** | `#news` | 3 news cards (exam hours, new collection, digital reader) |
| **FAQs** | `#faq` | 6 expandable FAQ items using `<details>` elements |
| Contact | `#contact` | Contact info + form with CSRF |
| Footer | — | Brand, platform links (incl. News & FAQs), library links, copyright |

The public navigation bar includes hotlinks to all sections: **Features**, **How it works**, **News**, **FAQs**, **Contact**.

### Content Reveal Fix

When the user scrolls past the laser beam transition zone (progress >= 1), all `.beam-reveal` sections are force-revealed. This prevents sections from being stuck at `opacity: 0` if the physics loop stops before the beam passes over them.

---

## Architecture

```
sankofa-flask/
├── app/
│   ├── __init__.py            # create_app(), security headers, scheduler start
│   ├── config.py              # Config class, SECRET_KEY validation
│   ├── extensions.py          # db, bcrypt, login_manager, mail, csrf, migrate
│   ├── models.py              # 9 SQLAlchemy models
│   ├── forms.py               # WTForms (registration, login, books, settings, …)
│   ├── routes/                # Blueprints
│   │   ├── auth.py            # /, /login, /register, /logout, /forgot-password, /contact
│   │   ├── student.py         # /student/*
│   │   ├── librarian.py       # /librarian/* (incl. /approvals)
│   │   ├── admin.py           # /admin/* (incl. /audit, /settings, /dashboard with charts)
│   │   └── catalog.py         # /catalog, /catalog/<id>
│   ├── templates/             # Jinja2 (base.html + per-blueprint folders)
│   ├── static/
│   │   ├── css/style.css      # Full design system + legacy component CSS
│   │   └── images/logo.png
│   └── utils/
│       ├── helpers.py         # log_action, get_setting, validators, send_notification_email
│       ├── fines.py           # calculate_fine, process_return, update_overdue_statuses
│       ├── notifications.py   # due-soon reminders, overdue digest, admin notices
│       ├── covers.py          # Open Library cover fetcher (hardened)
│       ├── decorators.py      # role_required, student_required, librarian_required, admin_required
│       └── i18n.py            # translation helper
├── migrations/                # Alembic migrations (Flask-Migrate)
├── uploads/books/             # Digital book files (served only after card verification)
├── seed.py                    # Sample data loader
├── run.py                     # Application entry point (port 5000)
├── requirements.txt
├── .env.example
└── README.md
```

### Blueprints

| Blueprint  | URL prefix    | Auth gating                                          |
|------------|---------------|------------------------------------------------------|
| `auth_bp`  | `/`           | Public; login required for `/logout`                 |
| `student_bp` | `/student`  | `@student_required` (role == 'student')              |
| `librarian_bp` | `/librarian` | `@librarian_required` (role in 'librarian', 'admin') |
| `admin_bp` | `/admin`      | `@admin_required` (role == 'admin')                  |
| `catalog_bp` | `/catalog`  | `@login_required` (any authenticated user)           |

---

## Database Schema

Nine models, unchanged from the original:

1. **User** — `user_id`, `student_id`, `username`, `full_name`, `email`, `password_hash`, `role` (student/librarian/admin), `department`, `year_of_study`, `is_active`, `approval_status` (pending/approved/rejected), `created_at`, `updated_at`, `profile_photo`, `email_notifications`, `theme_preference`, `language_preference`, **`must_change_password`**, **`failed_login_attempts`**, **`locked_until`**, **`last_login_at`** (last four added in FLASK-ADAPT).
2. **LibraryCard** — `card_id`, `user_id` (unique), `card_number` (unique), `issued_date`, `is_valid`, timestamps.
3. **Book** — `book_id`, `title`, `author`, `isbn`, `publisher`, `year_published`, `category`, `subcategory`, `total_physical_copies`, `available_physical_copies`, `has_digital`, `digital_file_path`, `cover_image`, `is_active`, timestamps.
4. **Checkout** — `checkout_id`, `user_id`, `book_id`, `librarian_id`, `checkout_date`, `expected_return_date`, `actual_return_date`, `status` (active/returned/overdue), timestamps.
5. **Fine** — `fine_id`, `checkout_id` (unique), `user_id`, `days_overdue`, `amount_per_day`, `total_amount`, `status` (pending/issued/waived/paid), `waiver_reason`, `processed_by`, timestamps.
6. **ReadingSession** — `session_id`, `user_id`, `book_id`, `card_verified`, `session_start`, `session_end`, timestamps.
7. **AuditLog** — `log_id`, `actor_id`, `action_type`, `target_table`, `target_id`, `description`, `created_at`.
8. **SystemSetting** — `setting_id`, `setting_key` (unique), `setting_value`, `description`, `updated_at`.
9. **Report** — `id`, `report_type`, `title`, `student_name`, `student_id`, `book_title`, `description`, `severity`, `filed_by`, `date_filed`.

The database is **SQLite (dev) or MySQL (prod)** — unchanged. SQLAlchemy is the ORM, so no application code changes when switching engines.

---

## Background Scheduler

`_start_overdue_scheduler()` (in `app/__init__.py`) launches a `BackgroundScheduler` with two jobs:

| Job                        | Interval | Action                                                              |
|----------------------------|----------|---------------------------------------------------------------------|
| `update_overdue_statuses`  | 1 hour   | Mark active checkouts past due as `overdue`; **refresh stale fines** (FLASK-ADAPT). |
| `send_due_soon_reminders`  | 24 hours | Email students whose books are due in 2 days.                       |

The scheduler only starts when `TESTING` is falsy, so it doesn't fire during unit tests.

---

## Environment Variables

Documented in `.env.example`:

| Variable                  | Default                              | Purpose                                                        |
|---------------------------|--------------------------------------|----------------------------------------------------------------|
| `SECRET_KEY`              | `dev-secret-key-change-in-production`| Flask session signing — **must override in production**.       |
| `DATABASE_URL`            | `sqlite:///sankofa_library.db`       | SQLAlchemy database URI.                                       |
| `SESSION_COOKIE_SECURE`   | `false`                              | Set `true` over HTTPS in production.                           |
| `MAIL_SERVER`             | `localhost`                          | Outbound SMTP server.                                          |
| `MAIL_PORT`               | `587`                                | SMTP port.                                                     |
| `MAIL_USE_TLS`            | `true`                               | Toggle STARTTLS.                                               |
| `MAIL_USERNAME`           | _(empty)_                            | SMTP auth user.                                                |
| `MAIL_PASSWORD`           | _(empty)_                            | SMTP auth password.                                            |
| `MAIL_DEFAULT_SENDER`     | `noreply@sankofa-library.edu`        | From: address.                                                 |
| `MAIL_SUPPRESS_SEND`      | `true`                               | Suppress actual email sends (dev default).                     |
| `STUDENT_EMAIL_DOMAIN`    | `st.knust.edu.gh`                    | Required email domain for student self-registration (seeded).  |
| `CURRENCY_SYMBOL`         | `GHS`                                | Currency symbol shown across the app (seeded).                 |
| `RATELIMIT_STORAGE_URI`   | _(optional)_                         | Redis URI for shared Flask-Limiter state across workers.       |

---

## Comparison with Next.js Version

| Concern                 | Next.js version (`/home/z/my-project`)                       | Flask version (`/home/z/my-project/sankofa-flask`)                      |
|-------------------------|--------------------------------------------------------------|---------------------------------------------------------------|
| Framework               | Next.js 16 + React 19                                        | Flask 3 + Jinja2                                              |
| ORM                     | Prisma                                                       | SQLAlchemy + Flask-SQLAlchemy                                 |
| Auth                    | JWT triple-channel (cookie + `Authorization` header + `auth_token` query param) | Flask-Login server sessions (signed cookie)                   |
| Middleware              | `src/proxy.ts` (edge)                                        | `@login_required` + `@role_required` decorators               |
| UI library              | shadcn/ui + Tailwind v4                                      | Hand-rolled CSS matching the same design tokens               |
| Charts                  | Recharts                                                     | Chart.js 4.4.4                                                |
| Animations              | Framer Motion                                                | CSS keyframes + IntersectionObserver reveal                   |
| Background jobs         | API route triggered on traffic                               | APScheduler `BackgroundScheduler` (1h / 24h intervals)        |
| Rate limiting           | Custom in-memory counter                                     | DB-backed failed-attempt counter + lockout; Flask-Limiter dep |
| File validation         | magic-byte sniffing in API route                             | `validate_image_upload()` / `validate_book_file_upload()`      |
| Security headers        | `next.config.js` headers                                     | `@app.after_request`                                          |
| CSRF                    | SameSite=strict + JWT                                        | Flask-WTF `CSRFProtect` on all forms                          |
| Database                | SQLite via Prisma                                            | SQLite (dev) / MySQL (prod) via SQLAlchemy                    |
| Port                    | 3000 (or gateway 81)                                         | 5000                                                          |
| Design tokens           | `src/app/globals.css`                                        | `app/static/css/style.css` (faithful port)                    |
| Fonts                   | Outfit + Inter via `next/font`                               | Outfit + Inter via Google Fonts `<link>`                      |

---

## Auth Differences: Flask server sessions vs Next.js JWT triple-channel

The Next.js version uses a **JWT triple-channel** delivery system so that auth works in cross-site iframes (where `SameSite=Lax` cookies are blocked):

1. **Cookie** — for same-site standalone tabs.
2. **`Authorization: Bearer <token>` header** — for fetch/XHR inside iframes (added via a fetch monkey-patch).
3. **`auth_token=<token>` URL query param** — for full page navigations inside iframes; the proxy sets the cookie on the response so subsequent navigations work without the param.

The Flask version uses **server-side sessions** via Flask-Login:

- The session is a single signed cookie set by Flask (`SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE=Lax`, `SESSION_COOKIE_SECURE` env-driven, 8-hour `PERMANENT_SESSION_LIFETIME`).
- There is no JWT, no `Authorization` header, no `auth_token` query param. The signed cookie is the only channel.
- This is simpler and more secure for a same-site standalone Flask service, but **does not work out of the box inside a cross-site iframe** because `SameSite=Lax` blocks the cookie.

If you need iframe embedding:

1. Set `SESSION_COOKIE_SAMESITE=None` and `SESSION_COOKIE_SECURE=true` (requires HTTPS).
2. Or front the Flask app with a reverse proxy that injects a bearer-token check.

The Next.js triple-channel pattern was specifically engineered for the preview-panel iframe use case; Flask's session-cookie approach is the conventional choice for standalone web apps.

---

## Tooltips and Confirmation Dialogs

The Flask version reproduces the Next.js tooltip + confirmation-dialog patterns using native HTML primitives:

### Tooltips

Every important icon-only button has a `title="…"` attribute (native browser tooltip) plus a visible text label wherever space allows. Examples:

- Sidebar nav items — `title="Dashboard — your loans, fines, and reading history"`, `title="Browse the full catalog of physical and digital books"`, etc.
- Logout button — `title="Sign out — sign out of your account"`, plus `aria-label="Sign out"`.
- Approve/Reject buttons — `title="Approve {full_name} — grants library access immediately"` / `title="Reject {full_name} — denies access permanently"`.
- Save Settings — `title="Save library policy — affects fines, loan periods, and checkout limits for all users"`.
- Audit search button — `title="Run the audit-log search with the current filters"`.
- Catalog "Read Online" — `title="Read this book in your browser — library card verification required"`.

### Confirmation dialogs

A small delegated click handler in `base.html` watches for any element with a `data-confirm="…"` attribute and runs `window.confirm()` before allowing the action. Destructive actions wired up:

- **Approve student** — `data-confirm="Approve {full_name}? They will be able to log in immediately. This action is logged in the audit trail."`
- **Reject student** — `data-confirm="Reject {full_name}? They will not be able to log in. This action is logged in the audit trail."`
- (Existing `confirm()`-style guards in other templates still work — the new system is purely additive.)

### Other UX improvements in `base.html`

- Skip-to-content link (`<a href="#main-content" class="skip-to-content">`) for keyboard users.
- Google Fonts preconnect + Outfit/Inter stylesheet.
- Favicon (`<link rel="icon">`).
- Meta description + Open Graph tags.
- Sidebar nav items now have Font Awesome icons + `aria-hidden` on the icon.
- Logout is a POST `<form>` with CSRF token (not a GET `<a>`).
- `aria-label` on every icon-only button.
- Breadcrumb region (`<nav class="breadcrumbs">`) on authenticated pages.
- Toast notification system — flashes are rendered as a JSON array and animated in by JS as slide-in toasts (top-right stack, auto-dismiss after 6s, manual close button). `<noscript>` fallback renders the old flash block.
- `.empty-state-component` for empty lists.
- `.skeleton-shimmer` loading placeholders (ready to drop into any loading view).
- `@media (prefers-reduced-motion: reduce)` disables animations.
- `@media print` with `.no-print` hides chrome when printing.

---

## License

This project is a faithful Python adaptation of the Sankofa Library System. See the original repository for license details.
