"""Application factory — wires up extensions, blueprints, security headers,
error handlers, scheduler, and default settings.

Faithful Flask port of the the design system app at the reference implementation
- 5 blueprints (auth, admin, librarian, student, catalog) with the same
  role gating as src/middleware.ts.
- Security headers via @app.after_request (CSP, X-Content-Type-Options,
  X-Frame-Options, HSTS, Referrer-Policy, Permissions-Policy).
- Background scheduler: update_overdue_statuses hourly,
  send_due_soon_reminders daily — implements the design system.
- init_default_settings() seeds the SystemSetting table on boot.
"""
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template
from werkzeug.exceptions import HTTPException


# Load .env (if present) before importing Config so env vars are visible.
load_dotenv()


def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the uploads folder exists.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ---- Extensions ----------------------------------------------------
    from app.extensions import bcrypt, csrf, db, login_manager, mail, migrate
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # ---- Logging -------------------------------------------------------
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # ---- Security headers via @app.after_request -----------------------
    @app.after_request
    def _apply_security_headers(response):
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com data:; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'self'"
        )
        response.headers.setdefault('Content-Security-Policy', csp)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault(
            'Referrer-Policy', 'strict-origin-when-cross-origin'
        )
        response.headers.setdefault(
            'Strict-Transport-Security',
            'max-age=31536000; includeSubDomains',
        )
        response.headers.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=()',
        )
        return response

    # ---- User loader ---------------------------------------------------
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    # ---- Blueprints ----------------------------------------------------
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.librarian import librarian_bp
    from app.routes.student import student_bp
    from app.routes.catalog import catalog_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(librarian_bp, url_prefix='/librarian')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(catalog_bp)

    # ---- Jinja globals / context processors ----------------------------
    from app.utils.i18n import current_language, t
    app.jinja_env.globals['t'] = t
    app.jinja_env.globals['current_language'] = current_language

    @app.context_processor
    def _inject_globals():
        from app.utils.helpers import get_currency_symbol, get_setting
        return {
            'now': datetime.utcnow(),
            'currency_symbol': get_currency_symbol(),
            'library_name': get_setting(
                'library_name',
                app.config.get('DEFAULT_LIBRARY_NAME', 'Sankofa Academic Library'),
            ),
        }

    # ---- Error handlers (403, 404) -------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(HTTPException)
    def handle_http(e):
        if e.code == 403:
            return render_template('errors/403.html'), 403
        if e.code == 404:
            return render_template('errors/404.html'), 404
        return render_template('errors/404.html'), e.code

    # ---- DB bootstrap + default settings -------------------------------
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table('users'):
            db.create_all()
        from app.utils.helpers import init_default_settings
        init_default_settings()

    # ---- Background scheduler ------------------------------------------
    if not app.config.get('TESTING'):
        try:
            _start_scheduler(app)
        except Exception as exc:  # pragma: no cover - safety net
            app.logger.warning('Scheduler could not start: %s', exc)

    return app


def _start_scheduler(app):
    """Hourly overdue refresh + daily due-soon reminders (FLASK-ADAPT).

    Mirrors the the design system scheduled jobs — keeps the DB consistent even
    when nobody is hitting the app.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.utils.fines import update_overdue_statuses
    from app.utils.notifications import send_due_soon_reminders

    def overdue_job():
        with app.app_context():
            try:
                update_overdue_statuses()
            except Exception as exc:  # pragma: no cover
                app.logger.error('overdue_job failed: %s', exc)

    def reminder_job():
        with app.app_context():
            try:
                send_due_soon_reminders()
            except Exception as exc:  # pragma: no cover
                app.logger.error('reminder_job failed: %s', exc)

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        overdue_job, 'interval', hours=1,
        id='update_overdue_statuses', replace_existing=True,
    )
    scheduler.add_job(
        reminder_job, 'interval', hours=24,
        id='send_due_soon_reminders', replace_existing=True,
    )
    scheduler.start()
