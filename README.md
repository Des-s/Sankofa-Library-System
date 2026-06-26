# Sankofa Library System

A web-based academic library management application built with **Flask**, **MySQL/SQLite**, and **HTML/CSS**.

## Features

- **Student portal** — registration with automatic library card issuance, catalog browsing, online reading with card verification, borrowing history, and fines
- **Librarian portal** — in-person checkout/return, overdue tracking, fine management, book catalog CRUD, student lookup, reports
- **Admin portal** — user management, system settings (fine rate, loan period, card format), audit log, analytics

## Quick Start

### 1. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional)

Copy `.env.example` to `.env` and adjust settings. By default the app uses SQLite for easy local development.

For MySQL:

```
DATABASE_URL=mysql+pymysql://user:password@localhost/sankofa_library
```

Create the database first:

```sql
CREATE DATABASE sankofa_library CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Seed sample data

```bash
python seed.py
```

### 5. Run the application

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000)

## Default Login Credentials (after seeding)

| Role      | Email                   | Password       |
|-----------|-------------------------|----------------|
| Admin     | admin@sankofa.edu       | admin12345     |
| Librarian | librarian@sankofa.edu   | librarian123   |
| Student   | student1@sankofa.edu    | student123     |

Student library cards are printed during seeding (format: `LIB-2026-STU2024001`).

## Project Structure

```
Library/
├── app/
│   ├── models.py          # SQLAlchemy models
│   ├── forms.py           # WTForms
│   ├── routes/            # Blueprints (auth, student, librarian, admin, catalog)
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/css/        # Stylesheets
│   └── utils/             # Helpers, fines, decorators
├── uploads/books/         # Digital book files (not web-accessible directly)
├── seed.py                # Sample data loader
├── run.py                 # Application entry point
└── requirements.txt
```

## Technology Stack

- **Backend:** Python 3, Flask, SQLAlchemy, Flask-Login, Flask-Bcrypt, Flask-WTF
- **Database:** MySQL (production) or SQLite (development)
- **Frontend:** HTML5, CSS3, Jinja2 templates

## Security

- Passwords hashed with bcrypt
- Role-based access control on all routes
- CSRF protection on all forms
- Digital books served only after library card verification
- All actions logged to audit trail
