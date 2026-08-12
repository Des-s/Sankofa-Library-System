"""Flask extension singletons — created once, bound to the app in create_app.

Faithful port of the Next.js dependency graph: SQLAlchemy (Prisma),
Flask-Login (JWT sessions), Flask-WTF (CSRF), Flask-Bcrypt (bcryptjs),
Flask-Mail (nodemailer), Flask-Migrate (Prisma migrate).
"""
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# Core persistence / ORM
db = SQLAlchemy()
# Password hashing (mirrors bcryptjs in src/lib/auth.ts)
bcrypt = Bcrypt()
# Session management (mirrors jose JWT cookies in src/lib/auth.ts)
login_manager = LoginManager()
# CSRF protection on every form / POST route (mirrors Next.js CSRF token check)
csrf = CSRFProtect()
# Outbound email (mirrors nodemailer in src/lib/notifications.ts)
mail = Mail()
# Database migrations (mirrors `prisma migrate`)
migrate = Migrate()

# Login flow defaults — match the Next.js /login redirect.
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
