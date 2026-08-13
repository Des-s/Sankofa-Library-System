"""Student blueprint — /student/* routes.

All routes require @login_required + @student_required.
before_request calls update_overdue_statuses() so the dashboard always
shows fresh overdue state.

Sankofa Library System student routes.

Routes:
- `/dashboard` — library card, active checkouts, outstanding fines,
  reading sessions.
- `/borrowings` — tabs: borrowed (active+overdue), history, reading.
- `/fines` — total outstanding, fines table.
- `/read/<book_id>` — card verification → create ReadingSession → show
  reader.
- `/read/<book_id>/end/<session_id>` — end session (POST with CSRF).
- `/read/<book_id>/content/<session_id>` — serve digital file (validate
  session).
- `/profile`, `/settings`.
"""
from datetime import datetime
from decimal import Decimal

from flask import (
    Blueprint, abort, flash, redirect, render_template, request,
    send_file, url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import (
    CardVerificationForm, ChangePasswordForm, LanguageForm,
    NotificationSettingsForm, ProfilePhotoForm, SupportRequestForm, ThemeForm,
)
from app.models import Book, Checkout, Fine, ReadingSession, Report
from app.utils.decorators import student_required
from app.utils.fines import update_overdue_statuses
from app.utils.helpers import log_action, save_profile_photo

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.before_request
def before_request():
    """Refresh overdue statuses before every student request."""
    update_overdue_statuses()


# ---------------------------------------------------------------------------
# /dashboard — library card + active checkouts + fines + reading sessions
# ---------------------------------------------------------------------------
@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    active_checkouts = (
        Checkout.query.filter_by(user_id=current_user.user_id)
        .filter(Checkout.status.in_(['active', 'overdue']))
        .all()
    )
    outstanding_fines = (
        Fine.query.filter_by(user_id=current_user.user_id)
        .filter(Fine.status.in_(['issued', 'pending']))
        .all()
    )
    recent_sessions = (
        ReadingSession.query.filter_by(user_id=current_user.user_id)
        .order_by(ReadingSession.session_start.desc())
        .limit(5).all()
    )
    card = current_user.library_card
    return render_template(
        'student/dashboard.html',
        card=card,
        active_checkouts=active_checkouts,
        outstanding_fines=outstanding_fines,
        recent_sessions=recent_sessions,
    )


# ---------------------------------------------------------------------------
# /profile, /settings
# ---------------------------------------------------------------------------
@student_bp.route('/profile')
@login_required
@student_required
def profile():
    password_form = ChangePasswordForm()
    photo_form = ProfilePhotoForm()
    return render_template(
        'student/profile.html',
        password_form=password_form,
        photo_form=photo_form,
        card=current_user.library_card,
    )


@student_bp.route('/settings')
@login_required
@student_required
def settings():
    notification_form = NotificationSettingsForm(
        email_notifications=current_user.email_notifications
    )
    theme_form = ThemeForm(dark_mode=(current_user.theme_preference == 'dark'))
    language_form = LanguageForm(language_preference=current_user.language_preference)
    support_form = SupportRequestForm()
    return render_template(
        'student/settings.html',
        notification_form=notification_form,
        theme_form=theme_form,
        language_form=language_form,
        support_form=support_form,
    )


@student_bp.route('/profile/password', methods=['POST'])
@login_required
@student_required
def change_password():
    password_form = ChangePasswordForm()
    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            log_action(
                'PASSWORD_CHANGE',
                f'Student changed their own password: {current_user.email}',
            )
            flash('Password updated successfully.', 'success')
    else:
        for errors in password_form.errors.values():
            for error in errors:
                flash(error, 'danger')
    return redirect(url_for('student.profile'))


@student_bp.route('/profile/photo', methods=['POST'])
@login_required
@student_required
def update_photo():
    photo_form = ProfilePhotoForm()
    if photo_form.validate_on_submit():
        save_profile_photo(current_user, photo_form.profile_photo.data)
        db.session.commit()
        flash('Profile photo updated.', 'success')
    return redirect(url_for('student.profile'))


@student_bp.route('/settings/notifications', methods=['POST'])
@login_required
@student_required
def update_notifications():
    notification_form = NotificationSettingsForm()
    if notification_form.validate_on_submit():
        current_user.email_notifications = notification_form.email_notifications.data
        db.session.commit()
        flash('Notification preferences saved.', 'success')
    return redirect(url_for('student.settings'))


@student_bp.route('/settings/theme', methods=['POST'])
@login_required
@student_required
def update_theme():
    theme_form = ThemeForm()
    if theme_form.validate_on_submit():
        current_user.theme_preference = (
            'dark' if theme_form.dark_mode.data else 'light'
        )
        db.session.commit()
        flash('Appearance updated.', 'success')
    return redirect(url_for('student.settings'))


@student_bp.route('/settings/language', methods=['POST'])
@login_required
@student_required
def update_language():
    language_form = LanguageForm()
    if language_form.validate_on_submit():
        current_user.language_preference = language_form.language_preference.data
        db.session.commit()
        flash('Language updated.', 'success')
    return redirect(url_for('student.settings'))


@student_bp.route('/settings/support', methods=['POST'])
@login_required
@student_required
def submit_support_request():
    support_form = SupportRequestForm()
    if support_form.validate_on_submit():
        report = Report(
            report_type='support',
            title=support_form.subject.data.strip(),
            description=support_form.description.data.strip(),
            student_id=current_user.user_id,
            student_name=current_user.full_name,
            filed_by=current_user.user_id,
        )
        db.session.add(report)
        db.session.commit()
        log_action(
            'SUPPORT_REQUEST',
            f'Support request filed: {report.title}',
            target_table='reports', target_id=report.id,
        )
        flash('Your report has been submitted to the library staff.', 'success')
    return redirect(url_for('student.settings'))


# ---------------------------------------------------------------------------
# /borrowings — tabs: borrowed / history / reading
# ---------------------------------------------------------------------------
@student_bp.route('/borrowings')
@login_required
@student_required
def borrowings():
    tab = request.args.get('tab', 'borrowed')
    checkouts = (
        Checkout.query.filter_by(user_id=current_user.user_id)
        .order_by(Checkout.checkout_date.desc()).all()
    )
    reading_sessions = (
        ReadingSession.query.filter_by(user_id=current_user.user_id)
        .order_by(ReadingSession.session_start.desc()).all()
    )
    return render_template(
        'student/borrowings.html',
        checkouts=checkouts,
        reading_sessions=reading_sessions,
        tab=tab,
    )


# ---------------------------------------------------------------------------
# /fines — total outstanding + fines table
# ---------------------------------------------------------------------------
@student_bp.route('/fines')
@login_required
@student_required
def fines():
    fines_list = (
        Fine.query.filter_by(user_id=current_user.user_id)
        .order_by(Fine.created_at.desc()).all()
    )
    outstanding = [f for f in fines_list if f.status in ('issued', 'pending')]
    total_outstanding = sum(
        (f.total_amount for f in outstanding), Decimal('0.00')
    )
    return render_template(
        'student/fines.html',
        fines=fines_list,
        total_outstanding=total_outstanding,
        outstanding_count=len(outstanding),
    )


# ---------------------------------------------------------------------------
# /read/<book_id> — card verification → create ReadingSession → show reader
# ---------------------------------------------------------------------------
@student_bp.route('/read/<int:book_id>', methods=['GET', 'POST'])
@login_required
@student_required
def read_book(book_id):
    book = Book.query.filter_by(
        book_id=book_id, is_active=True, has_digital=True
    ).first_or_404()
    form = CardVerificationForm()

    verified_session_id = request.args.get('session')

    if request.method == 'POST' and form.validate_on_submit():
        card = current_user.library_card
        if not card or not card.is_valid:
            flash('Your library card is invalid. Contact the library.', 'danger')
            log_action(
                'CARD_VERIFY_FAIL',
                f'Invalid card for user {current_user.email}',
                target_table='books', target_id=book_id,
            )
        elif form.card_number.data.strip().upper() != card.card_number.upper():
            flash('Library card number does not match your account.', 'danger')
            log_action(
                'CARD_VERIFY_FAIL',
                f'Wrong card entered by {current_user.email} for book {book.title}',
                target_table='books', target_id=book_id,
            )
        else:
            session = ReadingSession(
                user_id=current_user.user_id,
                book_id=book.book_id,
                card_verified=True,
            )
            db.session.add(session)
            db.session.commit()
            log_action(
                'READ_START',
                f'Student started reading "{book.title}"',
                target_table='reading_sessions',
                target_id=session.session_id,
            )
            return redirect(url_for(
                'student.read_book', book_id=book_id, session=session.session_id,
            ))

    active_session = None
    if verified_session_id:
        active_session = ReadingSession.query.filter_by(
            session_id=verified_session_id,
            user_id=current_user.user_id,
            book_id=book_id,
            card_verified=True,
        ).first()
        if not active_session:
            flash('Invalid reading session. Please verify your card again.', 'warning')
            return redirect(url_for('student.read_book', book_id=book_id))

    return render_template(
        'student/read.html', book=book, form=form, session=active_session,
    )


# ---------------------------------------------------------------------------
# /read/<book_id>/end/<session_id> — end session (POST with CSRF)
# ---------------------------------------------------------------------------
@student_bp.route('/read/<int:book_id>/end/<int:session_id>', methods=['POST'])
@login_required
@student_required
def end_reading(book_id, session_id):
    session = ReadingSession.query.filter_by(
        session_id=session_id,
        user_id=current_user.user_id,
        book_id=book_id,
    ).first_or_404()
    session.session_end = datetime.utcnow()
    db.session.commit()
    log_action(
        'READ_END',
        f'Student finished reading session #{session_id}',
        target_table='reading_sessions', target_id=session_id,
    )
    flash('Reading session ended.', 'info')
    return redirect(url_for('catalog.book_detail', book_id=book_id))


# ---------------------------------------------------------------------------
# /read/<book_id>/content/<session_id> — serve digital file (validate session)
# ---------------------------------------------------------------------------
@student_bp.route('/read/<int:book_id>/content/<int:session_id>')
@login_required
@student_required
def read_content(book_id, session_id):
    session = ReadingSession.query.filter_by(
        session_id=session_id,
        user_id=current_user.user_id,
        book_id=book_id,
        card_verified=True,
    ).first_or_404()
    if session.session_end:
        abort(403)

    book = Book.query.get_or_404(book_id)
    if not book.digital_file_path:
        abort(404)

    import os
    if not os.path.exists(book.digital_file_path):
        abort(404)

    return send_file(book.digital_file_path)
