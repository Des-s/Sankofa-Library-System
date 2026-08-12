"""Auth blueprint — public routes + login/logout/register/forgot-password.

Sankofa Library System auth API routes under src/app/api/auth/.
Routes:
- `/` (index) — public landing page. Passes real DB stats (book_count,
  student_count, category_count, total_copies, featured_books) to
  index.html. NOTE: index.html is already rewritten — DO NOT change the
  template call.
- `/login` — rate limiting (5 attempts → 15-min lock via
  failed_login_attempts + locked_until), audit logging, redirect to role
  dashboard.
- `/register` — student self-registration with email domain check,
  issues library card, approval_status='pending', notify admins.
- `/logout` — POST only with CSRF.
- `/forgot-password` — generate 16+ char secure temp password via
  secrets, never display, set must_change_password=True, audit log.
- `/news` — render resources.html with ContactForm.
- `/faq` — redirect to /news#faq-section.
- `/contact` — GET redirects to /news#contact-section, POST handles
  contact form.
"""
import secrets
import string
from datetime import datetime, timedelta
from smtplib import SMTPException

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from sqlalchemy import func

from app.extensions import db, mail
from app.forms import ContactForm, ForgotPasswordForm, LoginForm, RegistrationForm
from app.models import Book, LibraryCard, User
from app.utils.helpers import (
    generate_library_card_number, log_action, send_notification_email,
)
from app.utils.notifications import notify_admins_of_pending_registration


auth_bp = Blueprint('auth', __name__)


# ---------------------------------------------------------------------------
# Public landing page — index.html is already rewritten, DO NOT change the
# template call. Only the data passed in may evolve.
# ---------------------------------------------------------------------------
@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_librarian:
            return redirect(url_for('librarian.dashboard'))
        return redirect(url_for('student.dashboard'))

    # Real DB-driven stats — no hardcoded marketing numbers (FLASK-ADAPT).
    book_count = Book.query.filter_by(is_active=True).count()
    student_count = User.query.filter_by(
        role='student', approval_status='approved'
    ).count()
    category_count = Book.query.with_entities(Book.category).filter(
        Book.is_active.is_(True), Book.category.isnot(None)
    ).distinct().count()
    total_copies = db.session.query(
        func.sum(Book.total_physical_copies)
    ).filter(Book.is_active.is_(True)).scalar() or 0
    featured_books = (
        Book.query.filter_by(is_active=True)
        .order_by(Book.book_id.desc())
        .limit(4)
        .all()
    )
    return render_template(
        'index.html',
        book_count=book_count,
        student_count=student_count,
        category_count=category_count,
        total_copies=total_copies,
        featured_books=featured_books,
    )


# ---------------------------------------------------------------------------
# /news, /faq, /contact — informational pages
# ---------------------------------------------------------------------------
@auth_bp.route('/news')
def news():
    return redirect(url_for('auth.index') + '#features')


@auth_bp.route('/faq')
def faq():
    return redirect(url_for('auth.index') + '#how-it-works')


@auth_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        return redirect(url_for('auth.index') + '#contact')

    form = ContactForm()
    if form.validate_on_submit():
        msg = Message(
            subject=f'[Contact] {form.subject.data.strip()}',
            recipients=[current_app.config.get('MAIL_DEFAULT_SENDER')],
            reply_to=form.email.data.strip().lower(),
            body=(
                f'From: {form.name.data.strip()} '
                f'<{form.email.data.strip().lower()}>\n\n'
                f'{form.message.data.strip()}'
            ),
        )
        try:
            mail.send(msg)
        except (SMTPException, OSError) as exc:
            current_app.logger.error('contact form: mail send failed: %s', exc)
            flash(
                'Sorry, we could not send your message right now. '
                'Please try again later.',
                'danger',
            )
            return redirect(url_for('auth.news', _anchor='contact-section'))

        flash(
            'Thanks for reaching out! Our team will get back to you shortly.',
            'success',
        )
        return redirect(url_for('auth.news', _anchor='contact-section'))

    return render_template('resources.html', form=form, scroll_to='contact-section')


# ---------------------------------------------------------------------------
# /register — student self-registration (mirror src/app/api/auth/register)
# ---------------------------------------------------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            student_id=form.student_id.data.strip().upper(),
            username=form.username.data.strip().lower(),
            full_name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role='student',
            department=form.department.data.strip(),
            year_of_study=form.year_of_study.data,
            is_active=True,
            approval_status='pending',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        card_number = generate_library_card_number(user.student_id)
        card = LibraryCard(user_id=user.user_id, card_number=card_number)
        db.session.add(card)
        db.session.commit()

        log_action(
            'REGISTER',
            f'Student registered (pending approval): {user.full_name} '
            f'({user.student_id}). Card: {card_number}',
            target_table='users',
            target_id=user.user_id,
            actor_id=user.user_id,
        )
        notify_admins_of_pending_registration(user)

        flash(
            'Registration successful! Your account is pending approval by '
            'library staff. You will be able to log in once approved.',
            'info',
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


# ---------------------------------------------------------------------------
# /login — rate-limited login (mirror src/app/api/auth/login)
# ---------------------------------------------------------------------------
def _is_locked(user):
    """Return (locked, remaining_minutes) for an account under lockout."""
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
        return True, max(1, int(remaining) + 1)
    # Reset stale lockout window + counter once the window passes.
    if user.locked_until and user.locked_until <= datetime.utcnow():
        user.locked_until = None
        user.failed_login_attempts = 0
        db.session.commit()
    return False, 0


def _record_failed_login(user):
    """Increment the failed-attempt counter and lock the account if needed."""
    max_failures = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
    lockout_minutes = current_app.config.get('LOCKOUT_MINUTES', 15)

    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= max_failures:
        user.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
        log_action(
            'ACCOUNT_LOCKED',
            f'Account locked after {user.failed_login_attempts} failed '
            f'logins: {user.email}',
            target_table='users',
            target_id=user.user_id,
        )
    else:
        log_action(
            'LOGIN_FAILED',
            f'Failed login attempt {user.failed_login_attempts}/{max_failures} '
            f'for {user.email}',
            target_table='users',
            target_id=user.user_id,
        )
    db.session.commit()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        # 1) Unknown email — generic failure, audit it.
        if not user:
            log_action('LOGIN_FAILED', f'Failed login for unknown email: {email}')
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', form=form)

        # 2) Locked account — block regardless of password.
        locked, minutes_left = _is_locked(user)
        if locked:
            flash(
                f'Too many failed login attempts. Please try again in '
                f'{minutes_left} minute(s).',
                'danger',
            )
            return render_template('auth/login.html', form=form)

        # 3) Password check.
        if not user.check_password(form.password.data):
            _record_failed_login(user)
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', form=form)

        # 4) Account-state checks.
        if not user.is_active:
            flash(
                'Your account has been deactivated. Contact the library.',
                'danger',
            )
            return render_template('auth/login.html', form=form)
        if user.approval_status == 'pending':
            flash(
                'Your account is still pending approval by library staff.',
                'warning',
            )
            return render_template('auth/login.html', form=form)
        if user.approval_status == 'rejected':
            flash(
                'Your registration was not approved. Contact the library '
                'for details.',
                'danger',
            )
            return render_template('auth/login.html', form=form)

        # 5) Successful login — reset counters.
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        login_user(user)
        log_action('LOGIN', f'User logged in: {user.email}', actor_id=user.user_id)
        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect(url_for('auth.index'))

    return render_template('auth/login.html', form=form)


# ---------------------------------------------------------------------------
# /logout — POST only, CSRF-protected (FLASK-ADAPT)
# ---------------------------------------------------------------------------
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """POST-only logout — CSRF token enforced by Flask-WTF globally."""
    log_action('LOGOUT', f'User logged out: {current_user.email}')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# /forgot-password — secure temp password (FLASK-ADAPT)
# ---------------------------------------------------------------------------
def generate_temp_password(length=20):
    """Generate a cryptographically secure temp password.

    At least 16 chars from a mixed alphabet — never displayed on screen,
    only ever sent through the email channel.
    """
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*-_=+'
    # Guarantee at least one of each class to satisfy strength checks.
    mandatory = (
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
    )
    rest = ''.join(
        secrets.choice(alphabet) for _ in range(max(length, 16) - len(mandatory))
    )
    return mandatory + rest


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(User.email.ilike(email)).first()

        if user:
            temp_password = generate_temp_password()
            user.set_password(temp_password)
            user.must_change_password = True
            # Reset failed-login state in case they were locked out.
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()

            # NEVER display the temp password on screen.
            msg = Message(
                subject='Your Sankofa Library Temporary Password',
                recipients=[user.email],
                body=(
                    f'Hello {user.full_name},\n\n'
                    f'A password reset was requested for your account.\n'
                    f'Your temporary password is: {temp_password}\n\n'
                    f'Please log in and change your password as soon as '
                    f'possible.\n\n'
                    f'If you did not request this, please contact a '
                    f'librarian immediately.'
                ),
            )
            send_notification_email(msg, suppress_errors=True)

            log_action(
                'PASSWORD_RESET',
                f'Temporary password issued for {user.email} '
                f'(must_change_password set)',
                target_table='users',
                target_id=user.user_id,
            )

        # Generic message — no information disclosure.
        flash(
            'If that email is registered, a temporary password has been sent '
            'to it. You will be required to change it after logging in.',
            'info',
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)
