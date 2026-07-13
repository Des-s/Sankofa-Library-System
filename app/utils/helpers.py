import os
from datetime import date
from decimal import Decimal

from flask import current_app
from flask_login import current_user
from werkzeug.utils import secure_filename

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


def get_max_active_checkouts():
    val = get_setting('max_active_checkouts')
    if val is not None:
        return int(val)
    return int(current_app.config.get('DEFAULT_MAX_ACTIVE_CHECKOUTS', 5))


def generate_library_card_number(student_id):
    card_format = get_card_format()
    year = date.today().year
    return card_format.format(year=year, student_id=student_id.upper())


def get_checkouts_by_department():
    """Count of checkouts (borrowed/read) per student department, for pie charts."""
    from app.models import Checkout, User

    rows = (
        db.session.query(User.department, db.func.count(Checkout.checkout_id))
        .join(Checkout, Checkout.user_id == User.user_id)
        .filter(User.department.isnot(None))
        .group_by(User.department)
        .order_by(db.func.count(Checkout.checkout_id).desc())
        .all()
    )
    return [(dept or 'Unspecified', count) for dept, count in rows]


def get_user_signups_by_month(months=6):
    """Count of new user registrations per month, most recent `months` months, for a growth chart."""
    from app.models import User

    today = date.today()
    month_starts = []
    y, m = today.year, today.month
    for _ in range(months):
        month_starts.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    month_starts.reverse()

    buckets = []
    for i, start in enumerate(month_starts):
        end = month_starts[i + 1] if i + 1 < len(month_starts) else (
            date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
        )
        count = User.query.filter(User.created_at >= start, User.created_at < end).count()
        buckets.append((start.strftime('%b %Y'), count))
    return buckets


def get_book_availability_rate():
    """% of physical copies currently on the shelf (not checked out), across active books."""
    from app.models import Book

    totals = db.session.query(
        db.func.sum(Book.total_physical_copies), db.func.sum(Book.available_physical_copies)
    ).filter(Book.is_active == True, Book.total_physical_copies > 0).first()  # noqa: E712
    total, available = totals
    if not total:
        return 0
    return round((available or 0) / total * 100)


def get_on_time_return_rate():
    """% of returned checkouts that came back on or before the due date."""
    from app.models import Checkout

    returned = Checkout.query.filter(Checkout.status == 'returned').all()
    if not returned:
        return 0
    on_time = sum(1 for c in returned if c.actual_return_date and c.actual_return_date <= c.expected_return_date)
    return round(on_time / len(returned) * 100)


def get_digital_coverage_rate():
    """% of active books that have a digital copy available."""
    from app.models import Book

    total = Book.query.filter(Book.is_active == True).count()  # noqa: E712
    if not total:
        return 0
    digital = Book.query.filter(Book.is_active == True, Book.has_digital == True).count()  # noqa: E712
    return round(digital / total * 100)


def get_fine_collection_rate():
    """% of all issued fine value (by amount) that has actually been paid."""
    from app.models import Fine

    total = db.session.query(db.func.sum(Fine.total_amount)).filter(
        Fine.status.in_(['paid', 'issued', 'pending'])
    ).scalar()
    if not total:
        return 0
    paid = db.session.query(db.func.sum(Fine.total_amount)).filter(Fine.status == 'paid').scalar() or 0
    return round(float(paid) / float(total) * 100)


def save_profile_photo(user, photo):
    if not photo or not photo.filename:
        return
    ext = photo.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f'user_{user.user_id}.{ext}')
    photos_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_photos')
    os.makedirs(photos_folder, exist_ok=True)
    photo.save(os.path.join(photos_folder, filename))
    user.profile_photo = filename


def init_default_settings():
    defaults = [
        ('fine_rate_per_day', str(current_app.config.get('DEFAULT_FINE_RATE', 1.00)), 'Daily fine rate in GHS'),
        ('loan_period_days', str(current_app.config.get('DEFAULT_LOAN_PERIOD_DAYS', 14)), 'Maximum loan period in days'),
        ('library_card_format', current_app.config.get('DEFAULT_CARD_FORMAT', 'LIB-{year}-{student_id}'), 'Library card number format'),
        ('max_active_checkouts', str(current_app.config.get('DEFAULT_MAX_ACTIVE_CHECKOUTS', 5)), 'Maximum active checkouts allowed per student'),
    ]
    for key, value, desc in defaults:
        if not SystemSetting.query.filter_by(setting_key=key).first():
            db.session.add(SystemSetting(setting_key=key, setting_value=value, description=desc))
    db.session.commit()
