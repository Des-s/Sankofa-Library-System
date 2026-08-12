# Sankofa Library System

A web-based academic library management application built with **Flask**, **SQLAlchemy**, **Jinja2**, and a warm Afrocentric design system. 

> "Sankofa" is an Akan word meaning *"go back and fetch it"* — the wisdom of learning from the past as you move forward. This project digitises academic library operations for the whole campus: catalog search, physical borrowing, online reading, fines, and audit-grade reporting.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Demo Credentials](#demo-credentials)
3. [Design System](#design-system)
4. [Security Features](#security-features)
5. [Features by Role](#features-by-role)
6. [Architecture](#architecture)
7. [Database Schema](#database-schema)
8. [Background Scheduler](#background-scheduler)
9. [Environment Variables](#environment-variables)

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and adjust as needed. By default, the app uses SQLite for local development.

```bash
cp .env.example .env
```

### 3. Seed sample data

```bash
python seed.py
```

### 4. Run

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000). The app runs as a standalone Flask service on port 5000.

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

Library cards are issued automatically during seeding (e.g., format `LIB-2026-STU2024001`).

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
- **Audit Log**: Track system-wide actions.
- **System Settings**: Configure library policies (e.g., maximum checkouts, loan periods, fine rates).
- **User Management**: Manage all users, including assigning roles.

---

## Architecture

- **Backend**: Python 3, Flask, Blueprint routing.
- **Database**: SQLite (dev) / MySQL/PostgreSQL (prod) via SQLAlchemy.
- **Frontend**: Jinja2 templates, vanilla JavaScript, vanilla CSS.
- **Forms**: WTForms + Flask-WTF.
- **Auth**: Flask-Login + Bcrypt.
- **Background Jobs**: APScheduler.

---

## Database Schema

Key entities:
- `User`: Base identity.
- `LibraryCard`: Assigned to approved students.
- `Book`: Title, author, ISBN, category.
- `Checkout`: Borrowing records linked to `User` and `Book`.
- `Fine`: Financial penalties for late returns.
- `ReadingSession`: Digital reading activity logs.
- `AuditLog`: Immutable ledger of administrative and system events.

---

## Background Scheduler

A background scheduler runs via `APScheduler` (initialized in `app/__init__.py`) to automatically execute scheduled tasks, such as:
- Marking due books as `overdue`.
- Accruing daily fine amounts based on configured system rates.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask cryptographic key. **Must** be overridden in production. |
| `DATABASE_URL` | `sqlite:///sankofa_library.db` | Connection string for SQLAlchemy. |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` when deploying with HTTPS. |
