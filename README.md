# Sankofa Library System

A web-based academic library management application built with **Flask**, **SQLAlchemy**, **Jinja2**, and a warm Afrocentric design system.

> "Sankofa" is an Akan word meaning *"go back and fetch it"* — the wisdom of learning from the past as you move forward. This project digitises academic library operations for the whole campus: catalog search, physical borrowing, online reading, fines, and audit-grade reporting.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Creating Accounts](#creating-accounts)
3. [Design System](#design-system)
4. [Security Features](#security-features)
5. [Features by Role](#features-by-role)
6. [Architecture](#architecture)
7. [Database Schema](#database-schema)
8. [Background Scheduler](#background-scheduler)
9. [Environment Variables](#environment-variables)
10. [Known Gotchas](#known-gotchas)

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and adjust as needed. By default, the app uses SQLite for local development (`sankofa_library.db`, stored under `instance/`).

```bash
cp .env.example .env
```

### 3. Build the database

Schema is managed by Flask-Migrate/Alembic. On a fresh checkout with no existing database:

```bash
flask db upgrade
```

### 4. Create accounts

The database starts empty — there's no seed data pre-loaded. See [Creating Accounts](#creating-accounts) below to create an admin and librarian to log in with.

### 5. Run

```bash
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The app runs as a standalone Flask service on port 5000.

---

## Creating Accounts

There's no demo/seed data in the database by default — it starts empty after `flask db upgrade`. Two ways to populate it:

### Option A — Minimal (recommended for local dev)

Run `create_accounts.py` to create just an admin and a librarian account directly via the `User` model:

```bash
python create_accounts.py
```

This creates:

| Role      | Email                          | Password      |
|-----------|---------------------------------|----------------|
| Admin     | `admin@st.knust.edu.gh`         | `ChangeMe123`  |
| Librarian | `librarian@st.knust.edu.gh`     | `ChangeMe123`  |

Login is by **email**, not username. Change these passwords after first login — they're placeholders. Edit the values at the top of `create_accounts.py` if you want different credentials.

### Option B — Full sample dataset

`seed.py` populates a much richer dataset: 6 users (admin, librarian, 4 students), 15 books, checkouts, fines, a reading session, and audit log entries.

```bash
python seed.py
```

**⚠️ Warning:** `seed.py` calls `db.drop_all()` followed by `db.create_all()`. This **wipes your entire database and rebuilds every table directly from the current models, bypassing Alembic migrations entirely.** Running it after migrations have already been applied will desync your migration history from your actual schema (this is exactly what caused the "duplicate column" / "no such table" migration errors this project has already hit once). Only run `seed.py` on a database you're fully prepared to discard, and follow it with a review of `flask db heads` / `flask db upgrade` before trusting migrations again afterward.

If seeded, credentials are:

| Role      | Email                          | Password       |
|-----------|---------------------------------|----------------|
| Admin     | `admin@sankofa.edu`             | `admin12345`   |
| Librarian | `librarian@sankofa.edu`         | `librarian123` |
| Student   | `kwame.mensah@st.knust.edu.gh`  | `student123`   |
| Student   | `ama.osei@st.knust.edu.gh`      | `student123`   |
| Student   | `kofi.asante@st.knust.edu.gh`   | `student123`   |
| Student (pending) | `akosua.frimpong@st.knust.edu.gh` | `student123` |

Library cards are issued automatically for seeded students (e.g., format `LIB-2026-STU2024001`).

> The login page's old "demo accounts — click to autofill" quick-fill card has been removed from the UI. Use the credentials above manually.

---

## Design System

All design decisions live in `app/static/css/style.css` utilizing custom CSS variables. The system implements a robust Afrocentric aesthetic.

### Color palette
- **Forest Green** (`#1B4332`): Primary brand color.
- **Gold** (`#B8860B`): Accent color.
- **Warm Off-White** (`#FDF8F0`): Paper-like background.
- **Deep Brown** (`#2C1810`): Main text color.

### Key Components
- **Kente Bar**: A woven-pattern visual accent used on library cards, stat widgets, and headers.
- **Gradient Badges**: Premium styling for interactive elements.
- **Dark Mode**: Fully supported via the `data-theme='dark'` attribute, reversing the palette to rich dark tones.
- **Reveal-on-scroll**: Public homepage sections use `.reveal` / `.beam-reveal` classes driven by an `IntersectionObserver` in `base.html`. If sections ever render invisible again, check that script for typos before assuming a CSS issue.

---

## Security Features

The application incorporates a robust set of security best practices:
- **CSRF Protection**: Enabled globally via `flask_wtf.CSRFProtect`.
- **SQL Injection Prevention**: Data is accessed via the SQLAlchemy ORM; no raw SQL queries are permitted.
- **XSS Prevention**: Jinja2 auto-escaping is active across all templates.
- **Role-Based Access Control (RBAC)**: Enforced via route decorators (`@admin_required`, `@librarian_required`, `@student_required`).
- **File Upload Defenses**: Uses `secure_filename` and conducts magic-byte content validation on image uploads.

---

## Features by Role

### 1. Student
- **Dashboard**: View active checkouts, overdue alerts, and outstanding fines.
- **Library Card**: View digital card with Kente styling.
- **Catalog**: Search books, view availability.
- **Digital Reading Room**: Open digital books (PDF/TXT) via a secure, verifiable iframe reader.

### 2. Librarian
- **Circulation Desk**: Process physical checkouts and returns.
- **Patron Management**: View student records and approve new sign-ups.
- **Fines**: Log and waive fines for late returns.
- **Catalog Management**: Add or edit physical and digital book listings, including cover uploads.

### 3. Administrator
- **Dashboard Analytics**: View macro-level metrics (User Growth, Checkout Volume, Category Distribution).
- **Audit Log**: Track system-wide actions, filterable by action type and target table.
- **System Settings**: Configure library policies (e.g., maximum checkouts, loan periods, fine rates).
- **User Management**: Manage all users, including assigning roles.

---

## Architecture

- **Backend**: Python 3, Flask, Blueprint routing.
- **Database**: SQLite (dev) / MySQL/PostgreSQL (prod) via SQLAlchemy, schema managed by Flask-Migrate/Alembic.
- **Frontend**: Jinja2 templates, vanilla JavaScript, vanilla CSS.
- **Forms**: WTForms + Flask-WTF.
- **Auth**: Flask-Login + Bcrypt.
- **Background Jobs**: APScheduler.

---

## Database Schema

Key entities:
- `User`: Base identity.
- `LibraryCard`: Assigned to approved students.
- `Book`: Title, author, ISBN, category, description.
- `Checkout`: Borrowing records linked to `User` and `Book`.
- `Fine`: Financial penalties for late returns.
- `ReadingSession`: Digital reading activity logs.
- `AuditLog`: Immutable ledger of administrative and system events (includes `ip_address`, `target_table`, `target_id`).

Schema changes go through Flask-Migrate:

```bash
flask db migrate -m "describe the change"
flask db upgrade
```

---

## Background Scheduler

A background scheduler runs via `APScheduler` (initialized in `app/__init__.py`) to automatically execute scheduled tasks, such as:
- Marking due books as `overdue`.
- Accruing daily fine amounts based on configured system rates.

Note: the scheduler starts on **every** `flask` CLI invocation (including `flask db upgrade`, `flask db migrate`, etc.), not just `python run.py` — this is expected and harmless, but explains why scheduler log lines appear during migration commands.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask cryptographic key. **Must** be overridden in production. |
| `DATABASE_URL` | `sqlite:///sankofa_library.db` | Connection string for SQLAlchemy. Resolves to `instance/sankofa_library.db` in practice — check there, not the project root, if debugging the actual db file. |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` when deploying with HTTPS. |

---

## Known Gotchas

A few issues surfaced during development that are worth knowing about if they recur:

- **`db.create_all()` vs. Alembic**: The app factory (`app/__init__.py`) previously called `db.create_all()` on boot, which conflicts with Alembic-managed migrations and causes `duplicate column` / `no such table` errors. This has been removed — schema changes should go through `flask db migrate` / `flask db upgrade` only. `seed.py` still uses `db.drop_all()` / `db.create_all()` internally (see [Creating Accounts](#creating-accounts) for the implications of running it).
- **Database file location**: SQLite file lives under `instance/`, not the project root, even though `DATABASE_URL` just says `sqlite:///sankofa_library.db`. A stray `sankofa_library.db` or `library.db` in the project root is not the real database.
- **`init_default_settings()` timing**: This seeds `SystemSetting` rows and must run *after* migrations have created the tables — it's called from `run.py`, not from inside `create_app()`, to avoid querying tables that don't exist yet during `flask db` commands.
- **Corrupted identifiers**: Watch for mangled references like `AuditLogarchiveget_table` or `entryarchiveget` (should be `AuditLog.target_table` and `entry.target`) — this pattern has shown up more than once in this codebase, likely from an editor/autocomplete issue, and silently breaks things (a `NameError` server-side, or a silently-failing `IntersectionObserver` client-side).