"""Flask extension singletons — created once, bound to the app in create_app.

Sankofa Library System dependency graph: SQLAlchemy,
Flask-Login, Flask-WTF (CSRF), Flask-Bcrypt,
Flask-Mail, Flask-Migrate.
"""
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# Core persistence / ORM
db = SQLAlchemy()
# Password hashing (password hashing)
bcrypt = Bcrypt()
# Session management (session management)
login_manager = LoginManager()

csrf = CSRFProtect()
# Outbound email (outbound email)
mail = Mail()
# Database migrations (database migrations)
migrate = Migrate()


login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
