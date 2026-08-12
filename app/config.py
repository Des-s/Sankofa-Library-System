"""Application configuration — Sankofa Library System design system
and security model.

Environment variables mirror the the design system .env exactly where possible.
All defaults match the seed-time SystemSetting values seeded by
scripts/seed.ts so the app is consistent out of the box.
"""
import os
import warnings
from datetime import timedelta


# Default SECRET_KEY — used when the env var is missing. Always warns.
_DEFAULT_SECRET_KEY = 'dev-secret-key-change-in-production'


class Config:
    # ---- Core -----------------------------------------------------------
    SECRET_KEY = os.environ.get('SECRET_KEY', _DEFAULT_SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///sankofa_library.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    # ---- Uploads (book digital files) ---------------------------------
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'uploads', 'books',
    )
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_BOOK_EXTENSIONS = {'pdf', 'txt', 'html', 'htm'}
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    # Magic-byte signatures for image validation (FLASK-ADAPT)
    IMAGE_MAGIC_BYTES = {
        'jpg': b'\xff\xd8\xff',
        'jpeg': b'\xff\xd8\xff',
        'png': b'\x89PNG\r\n\x1a\n',
    }


    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get(
        'SESSION_COOKIE_SECURE', 'false'
    ).lower() == 'true'
    SESSION_PERMANENT = True

    # ---- Auth lockout policy (mirrors src/lib/auth.ts lockout) -------
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15

    # ---- Mail server (mirrors nodemailer config) --------------------
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER', 'noreply@sankofa-library.edu'
    )
    MAIL_SUPPRESS_SEND = os.environ.get(
        'MAIL_SUPPRESS_SEND', 'true'
    ).lower() == 'true'


    DEFAULT_FINE_RATE = 1.00
    DEFAULT_LOAN_PERIOD_DAYS = 14
    DEFAULT_CARD_FORMAT = 'LIB-{year}-{student_id}'
    DEFAULT_MAX_ACTIVE_CHECKOUTS = 5
    DEFAULT_STUDENT_EMAIL_DOMAIN = 'st.knust.edu.gh'
    DEFAULT_CURRENCY_SYMBOL = 'GHS'
    DEFAULT_LIBRARY_NAME = 'Sankofa Academic Library'
    DEFAULT_LIBRARY_ADDRESS = 'Kumasi, Ghana'

    # ---- Cover fetcher safety (FLASK-ADAPT) -------------------------
    COVER_REQUEST_TIMEOUT = 10
    MAX_COVER_BYTES = 5 * 1024 * 1024  # 5 MB


    SCHEDULER_OVERDUE_INTERVAL_HOURS = 1
    SCHEDULER_REMINDER_INTERVAL_HOURS = 24

    @staticmethod
    def is_production():
        return (
            os.environ.get('FLASK_ENV') == 'production'
            or os.environ.get('ENV') == 'production'
        )


def _validate_secret_key():
    """Refuse to start in production with the default SECRET_KEY, warn in dev.

    Mirrors the the design system requirement that AUTH_SECRET is set to a strong value.
    """
    key = os.environ.get('SECRET_KEY', _DEFAULT_SECRET_KEY)
    if key == _DEFAULT_SECRET_KEY:
        if Config.is_production():
            raise RuntimeError(
                'FATAL: SECRET_KEY is using the default development value. '
                'Set the SECRET_KEY environment variable to a strong random '
                'value before running in production.'
            )
        warnings.warn(
            'WARNING: SECRET_KEY is using the default development value. '
            'Set the SECRET_KEY environment variable to a strong random '
            'value in production.',
            RuntimeWarning,
            stacklevel=2,
        )


# Validate on import — fail fast.
_validate_secret_key()
