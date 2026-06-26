import os
from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for, abort
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms import CardVerificationForm, ProfileForm
from app.models import Book, Checkout, Fine, ReadingSession, User
from app.utils.decorators import student_required
from app.utils.helpers import log_action

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    active_checkouts = Checkout.query.filter_by(user_id=current_user.user_id).filter(
        Checkout.status.in_(['active', 'overdue'])
    ).all()
    outstanding_fines = Fine.query.filter_by(user_id=current_user.user_id).filter(
        Fine.status.in_(['issued', 'pending'])
    ).all()
    recent_sessions = ReadingSession.query.filter_by(user_id=current_user.user_id).order_by(
        ReadingSession.session_start.desc()
    ).limit(5).all()
    card = current_user.library_card
    return render_template(
        'student/dashboard.html',
        card=card,
        active_checkouts=active_checkouts,
        outstanding_fines=outstanding_fines,
        recent_sessions=recent_sessions,
    )


@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@student_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        existing = User.query.filter(User.email == form.email.data, User.user_id != current_user.user_id).first()
        if existing:
            flash('That email is already in use.', 'danger')
        else:
            current_user.full_name = form.name.data.strip()
            current_user.email = form.email.data.strip().lower()
            current_user.department = form.department.data.strip()
            current_user.year_of_study = form.year_of_study.data

            photo = form.profile_photo.data
            if photo and photo.filename:
                ext = photo.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f'user_{current_user.user_id}.{ext}')
                photos_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_photos')
                os.makedirs(photos_folder, exist_ok=True)
                photo.save(os.path.join(photos_folder, filename))
                current_user.profile_photo = filename

            db.session.commit()
            log_action('PROFILE_UPDATE', f'Student updated profile: {current_user.email}')
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('student.profile'))
    return render_template('student/profile.html', form=form, card=current_user.library_card)


@student_bp.route('/borrowings')
@login_required
@student_required
def borrowings():
    checkouts = Checkout.query.filter_by(user_id=current_user.user_id).order_by(
        Checkout.checkout_date.desc()
    ).all()
    return render_template('student/borrowings.html', checkouts=checkouts)


@student_bp.route('/fines')
@login_required
@student_required
def fines():
    fines_list = Fine.query.filter_by(user_id=current_user.user_id).order_by(
        Fine.created_at.desc()
    ).all()
    return render_template('student/fines.html', fines=fines_list)


@student_bp.route('/read/<int:book_id>', methods=['GET', 'POST'])
@login_required
@student_required
def read_book(book_id):
    book = Book.query.filter_by(book_id=book_id, is_active=True, has_digital=True).first_or_404()
    form = CardVerificationForm()

    verified_session_id = request.args.get('session')

    if request.method == 'POST' and form.validate_on_submit():
        card = current_user.library_card
        if not card or not card.is_valid:
            flash('Your library card is invalid. Contact the library.', 'danger')
            log_action('CARD_VERIFY_FAIL', f'Invalid card for user {current_user.email}', target_table='books', target_id=book_id)
        elif form.card_number.data.strip().upper() != card.card_number.upper():
            flash('Library card number does not match your account.', 'danger')
            log_action('CARD_VERIFY_FAIL', f'Wrong card entered by {current_user.email} for book {book.title}', target_table='books', target_id=book_id)
        else:
            session = ReadingSession(
                user_id=current_user.user_id,
                book_id=book.book_id,
                card_verified=True,
            )
            db.session.add(session)
            db.session.commit()
            log_action('READ_START', f'Student started reading "{book.title}"', target_table='reading_sessions', target_id=session.session_id)
            return redirect(url_for('student.read_book', book_id=book_id, session=session.session_id))

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

    return render_template('student/read.html', book=book, form=form, session=active_session)


@student_bp.route('/read/<int:book_id>/end/<int:session_id>', methods=['POST'])
@login_required
@student_required
def end_reading(book_id, session_id):
    session = ReadingSession.query.filter_by(
        session_id=session_id,
        user_id=current_user.user_id,
        book_id=book_id,
    ).first_or_404()
    from datetime import datetime
    session.session_end = datetime.utcnow()
    db.session.commit()
    log_action('READ_END', f'Student finished reading session #{session_id}', target_table='reading_sessions', target_id=session_id)
    flash('Reading session ended.', 'info')
    return redirect(url_for('catalog.book_detail', book_id=book_id))


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
