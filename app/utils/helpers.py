from datetime import date
from decimal import Decimal

from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog, SystemSetting


def log_action(action_type, description, target_table=None, target_id=None, actor_id=None):
    actor = actor_id if actor_id is not None else (current_user.user_id if current_user.is_authenticated else None)
    entry = AuditLog(
        actor_id=actor,
        action_type=action_type,
        target_table=target_table,
        target_id=target_id,
        description=description,
    )
    db.session.add(entry)
    db.session.commit()


def get_setting(key, default=None):
    setting = SystemSetting.query.filter_by(setting_key=key).first()
    if setting:
        return setting.setting_value
    return default


def get_fine_rate():
    val = get_setting('fine_rate_per_day')
    if val is not None:
        return Decimal(val)
    return Decimal(str(current_app.config.get('DEFAULT_FINE_RATE', 1.00)))


def get_loan_period_days():
    val = get_setting('loan_period_days')
    if val is not None:
        return int(val)
    return int(current_app.config.get('DEFAULT_LOAN_PERIOD_DAYS', 14))


def get_card_format():
    return get_setting('library_card_format', current_app.config.get('DEFAULT_CARD_FORMAT', 'LIB-{year}-{student_id}'))


def generate_library_card_number(student_id):
    card_format = get_card_format()
    year = date.today().year
    return card_format.format(year=year, student_id=student_id.upper())


def init_default_settings():
    defaults = [
        ('fine_rate_per_day', str(current_app.config.get('DEFAULT_FINE_RATE', 1.00)), 'Daily fine rate in GHS'),
        ('loan_period_days', str(current_app.config.get('DEFAULT_LOAN_PERIOD_DAYS', 14)), 'Maximum loan period in days'),
        ('library_card_format', current_app.config.get('DEFAULT_CARD_FORMAT', 'LIB-{year}-{student_id}'), 'Library card number format'),
    ]
    for key, value, desc in defaults:
        if not SystemSetting.query.filter_by(setting_key=key).first():
            db.session.add(SystemSetting(setting_key=key, setting_value=value, description=desc))
    db.session.commit()
