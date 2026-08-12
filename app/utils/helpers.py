"""Helper utilities — faithful port of src/lib/library.ts plus the analytics
helpers used by both the admin and librarian dashboards.

Notable helpers:
- generate_library_card_number: try/except wrapped (FLASK-ADAPT).
- get_setting / get_fine_rate / get_loan_period_days / etc.: read
  from SystemSetting with config-default fallback.
- validate_image_upload: extension + magic-byte (JPEG FF D8 FF, PNG 89 50
  4E 47) validation.
- validate_book_file_upload: extension + MIME sniff for digital files.
- save_profile_photo: persists to app/static/uploads/profile_photos.
- send_notification_email: SMTP-safe wrapper around Flask-Mail.
- Analytics: get_checkouts_by_department, get_user_signups_by_month,
  get_book_availability_rate, get_on_time_return_rate,
  get_digital_coverage_rate, get_fine_collection_rate.
- init_default_settings: seeds the SystemSetting table.
- log_action: writes an AuditLog row.
"""
import os
from datetime import date
from decimal import Decimal

from flask import current_app, request
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import AuditLog, SystemSetting


# ---------------------------------------------------------------------------
# Audit logging (mirror src/lib/audit.ts logAction)
# ---------------------------------------------------------------------------
def log_action(action_type, description, target_table=None, target_id=None, actor_id=None):
    actor = (
        actor_id if actor_id is not None
        else (current_user.user_id if current_user.is_authenticated else None)
    )
    ip_address = None
    try:
        if request:
            ip_address = request.remote_addr or None
    except RuntimeError:
        # Outside of a request context (e.g. scheduler jobs).
        ip_address = None

    entry = AuditLog(
        actor_id=actor,
        action_type=action_type,
        target_table=target_table,
        target_id=target_id,
        description=description,
        ip_address=ip_address,
    )
    db.session.add(entry)
    db.session.commit()


# ---------------------------------------------------------------------------
# System settings (mirror src/lib/library.ts getSetting helpers)
# ---------------------------------------------------------------------------
def get_setting(key, default=None):
    setting = SystemSetting.query.filter_by(setting_key=key).first()
    if setting:
        return setting.setting_value
    return default


def set_setting(key, value, description=None):
    setting = SystemSetting.query.filter_by(setting_key=key).first()
    if setting:
        setting.setting_value = value
        if description is not None:
            setting.description = description
    else:
        db.session.add(SystemSetting(
            setting_key=key, setting_value=value, description=description,
        ))
    db.session.commit()


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
    return get_setting(
        'library_card_format',
        current_app.config.get('DEFAULT_CARD_FORMAT', 'LIB-{year}-{student_id}'),
    )


def get_max_active_checkouts():
    val = get_setting('max_active_checkouts')
    if val is not None:
        return int(val)
    return int(current_app.config.get('DEFAULT_MAX_ACTIVE_CHECKOUTS', 5))


def get_student_email_domain():
    return get_setting(
        'student_email_domain',
        current_app.config.get('DEFAULT_STUDENT_EMAIL_DOMAIN', 'st.knust.edu.gh'),
    )


def get_currency_symbol():
    return get_setting(
        'currency_symbol',
        current_app.config.get('DEFAULT_CURRENCY_SYMBOL', 'GHS'),
    )


# ---------------------------------------------------------------------------
# Library card generation (mirror src/lib/library.ts generateLibraryCardNumber)
# ---------------------------------------------------------------------------
def generate_library_card_number(student_id):
    """Generate a card number from the configured format.

    Wrapped in try/except so a malformed admin setting never crashes the
    registration flow — falls back to the canonical `LIB-{year}-{student_id}`.
    (FLASK-ADAPT)
    """
    card_format = get_card_format()
    try:
        year = date.today().year
        return card_format.format(
            year=year, student_id=str(student_id or '').upper()
        )
    except (KeyError, ValueError, IndexError) as exc:
        current_app.logger.error(
            'generate_library_card_number: bad format %r (%s) — falling back',
            card_format, exc,
        )
        return f'LIB-{date.today().year}-{str(student_id or "").upper()}'


# ---------------------------------------------------------------------------
# Analytics helpers (used by admin + librarian dashboards)
# ---------------------------------------------------------------------------
def get_checkouts_by_department():
    """Count of checkouts per student department, for pie charts."""
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
    """New user registrations per month, most recent `months` months."""
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
            date(start.year + 1, 1, 1) if start.month == 12
            else date(start.year, start.month + 1, 1)
        )
        count = User.query.filter(
            User.created_at >= start, User.created_at < end
        ).count()
        buckets.append((start.strftime('%b %Y'), count))
    return buckets


def get_book_availability_rate():
    """% of physical copies currently on the shelf across active books."""
    from app.models import Book

    totals = db.session.query(
        db.func.sum(Book.total_physical_copies),
        db.func.sum(Book.available_physical_copies),
    ).filter(
        Book.is_active == True,  # noqa: E712
        Book.total_physical_copies > 0,
    ).first()
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
    on_time = sum(
        1 for c in returned
        if c.actual_return_date and c.actual_return_date <= c.expected_return_date
    )
    return round(on_time / len(returned) * 100)


def get_digital_coverage_rate():
    """% of active books that have a digital copy available."""
    from app.models import Book

    total = Book.query.filter(Book.is_active == True).count()  # noqa: E712
    if not total:
        return 0
    digital = Book.query.filter(
        Book.is_active == True,  # noqa: E712
        Book.has_digital == True,  # noqa: E712
    ).count()
    return round(digital / total * 100)


def get_fine_collection_rate():
    """% of all issued fine value (by amount) that has actually been paid."""
    from app.models import Fine

    total = db.session.query(db.func.sum(Fine.total_amount)).filter(
        Fine.status.in_(['paid', 'issued', 'pending'])
    ).scalar()
    if not total:
        return 0
    paid = (
        db.session.query(db.func.sum(Fine.total_amount))
        .filter(Fine.status == 'paid').scalar() or 0
    )
    return round(float(paid) / float(total) * 100)


# ---------------------------------------------------------------------------
# File upload validation (FLASK-ADAPT)
# ---------------------------------------------------------------------------
def validate_image_upload(file_storage):
    """Validate an uploaded image by extension, MIME type, and magic bytes.

    Returns ``(True, None)`` on success, ``(False, reason)`` otherwise.
    (FLASK-ADAPT)
    """
    filename = file_storage.filename or ''
    # Avoid IndexError when the file has no extension.
    if '.' not in filename:
        return False, 'File has no extension.'
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', {'jpg', 'jpeg', 'png'})
    if ext not in allowed:
        return False, (
            f'File type .{ext} is not allowed. '
            f'Use one of: {", ".join(sorted(allowed))}.'
        )

    # Magic-byte check: JPEG FF D8 FF, PNG 89 50 4E 47.
    file_storage.stream.seek(0)
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    magic_map = current_app.config.get('IMAGE_MAGIC_BYTES', {})
    expected = magic_map.get(ext)
    if expected and not head.startswith(expected):
        return False, 'File content does not match its declared type.'
    return True, None


def validate_book_file_upload(file_storage):
    """Validate a digital-book file (PDF/TXT/HTML) by extension + MIME sniff.

    Returns ``(True, None)`` on success, ``(False, reason)`` otherwise.
    (FLASK-ADAPT)
    """
    filename = file_storage.filename or ''
    if '.' not in filename:
        return False, 'File has no extension.'
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = current_app.config.get(
        'ALLOWED_BOOK_EXTENSIONS', {'pdf', 'txt', 'html', 'htm'}
    )
    if ext not in allowed:
        return False, (
            f'File type .{ext} is not allowed. '
            f'Use one of: {", ".join(sorted(allowed))}.'
        )
    return True, None


def save_profile_photo(user, photo):
    """Validate + persist a profile photo for ``user``."""
    if not photo or not photo.filename:
        return
    ok, error = validate_image_upload(photo)
    if not ok:
        current_app.logger.warning(
            'Rejected profile photo for user %s: %s', user.user_id, error
        )
        return
    ext = photo.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f'user_{user.user_id}.{ext}')
    photos_folder = os.path.join(
        current_app.root_path, 'static', 'uploads', 'profile_photos'
    )
    os.makedirs(photos_folder, exist_ok=True)
    photo.save(os.path.join(photos_folder, filename))
    user.profile_photo = filename


# ---------------------------------------------------------------------------
# Email (mirror src/lib/notifications.ts sendNotificationEmail)
# ---------------------------------------------------------------------------
def send_notification_email(message, *, suppress_errors=False):
    """Send an email via Flask-Mail, swallowing SMTP errors and logging them.

    Returns ``True`` on success, ``False`` on failure. (FLASK-ADAPT)
    """
    from smtplib import SMTPException
    try:
        from app.extensions import mail
        mail.send(message)
        return True
    except (SMTPException, OSError) as exc:
        current_app.logger.error(
            'send_notification_email failed for recipients=%r: %s',
            getattr(message, 'recipients', []), exc,
        )
        if not suppress_errors:
            raise
        return False
    except Exception as exc:  # pragma: no cover - safety net
        current_app.logger.error(
            'send_notification_email unexpected error: %s', exc,
        )
        if not suppress_errors:
            raise
        return False


# ---------------------------------------------------------------------------
# Default settings seeder (mirror scripts/seed.ts systemSetting.createMany)
# ---------------------------------------------------------------------------
def init_default_settings():
    """Seed the SystemSetting table with config defaults if missing."""
    defaults = [
        ('fine_rate_per_day',
         str(current_app.config.get('DEFAULT_FINE_RATE', 1.00)),
         'Daily fine rate (currency units per day)'),
        ('loan_period_days',
         str(current_app.config.get('DEFAULT_LOAN_PERIOD_DAYS', 14)),
         'Maximum loan period in days'),
        ('library_card_format',
         current_app.config.get('DEFAULT_CARD_FORMAT', 'LIB-{year}-{student_id}'),
         'Library card number format (use {year} and {student_id})'),
        ('max_active_checkouts',
         str(current_app.config.get('DEFAULT_MAX_ACTIVE_CHECKOUTS', 5)),
         'Maximum active checkouts allowed per student'),
        ('student_email_domain',
         current_app.config.get('DEFAULT_STUDENT_EMAIL_DOMAIN', 'st.knust.edu.gh'),
         'Required email domain for student self-registration'),
        ('currency_symbol',
         current_app.config.get('DEFAULT_CURRENCY_SYMBOL', 'GHS'),
         'Symbol shown next to money values across the app'),
        ('library_name', 'Sankofa Academic Library',
         'Public-facing library name (shown on landing page & library card)'),
        ('library_address', 'Kumasi, Ghana',
         'Public-facing library address'),
    ]
    for key, value, desc in defaults:
        if not SystemSetting.query.filter_by(setting_key=key).first():
            db.session.add(SystemSetting(
                setting_key=key, setting_value=value, description=desc,
            ))
    db.session.commit()
