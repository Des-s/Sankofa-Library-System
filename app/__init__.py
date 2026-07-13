import os

from dotenv import load_dotenv
from flask_migrate import Migrate


load_dotenv()


def create_app(config_class='app.config.Config'):
    from flask import Flask, render_template

    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.extensions import bcrypt, csrf, db, login_manager, mail
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)
  

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.librarian import librarian_bp
    from app.routes.admin import admin_bp
    from app.routes.catalog import catalog_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(librarian_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(catalog_bp)

    from app.utils.i18n import t
    app.jinja_env.globals['t'] = t

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table('users'):
            db.create_all()
        from app.utils.helpers import init_default_settings
        init_default_settings()

    if not app.config.get('TESTING'):
        _start_overdue_scheduler(app)

    return app


def _start_overdue_scheduler(app):
    """Periodically mark active checkouts as overdue and send due-soon reminders, independent of page traffic."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.utils.fines import update_overdue_statuses
    from app.utils.notifications import send_due_soon_reminders

    def overdue_job():
        with app.app_context():
            update_overdue_statuses()

    def reminder_job():
        with app.app_context():
            send_due_soon_reminders()

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(overdue_job, 'interval', hours=1, id='update_overdue_statuses', replace_existing=True)
    scheduler.add_job(reminder_job, 'interval', hours=24, id='send_due_soon_reminders', replace_existing=True)
    scheduler.start()
