import secrets
import string

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message

from app.extensions import db, mail
from app.forms import ContactForm, ForgotPasswordForm, LoginForm, RegistrationForm
from app.models import Book, LibraryCard, User
from app.utils.helpers import generate_library_card_number, log_action
from app.utils.notifications import notify_admins_of_pending_registration


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_librarian:
            return redirect(url_for('librarian.dashboard'))
        return redirect(url_for('student.dashboard'))

    book_count = Book.query.filter_by(is_active=True).count()
    student_count = User.query.filter_by(role='student', approval_status='approved').count()
    category_count = Book.query.with_entities(Book.category).filter(
        Book.is_active.is_(True), Book.category.isnot(None)
    ).distinct().count()
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
        featured_books=featured_books,
    )


@auth_bp.route('/news')
def news():
    return render_template('news.html')


@auth_bp.route('/faq')
def faq():
    return render_template('faq.html')


@auth_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = Message(
            subject=f'[Contact] {form.subject.data.strip()}',
            recipients=[current_app.config.get('MAIL_DEFAULT_SENDER')],
            reply_to=form.email.data.strip().lower(),
            body=(
                f'From: {form.name.data.strip()} <{form.email.data.strip().lower()}>\n\n'
                f'{form.message.data.strip()}'
            ),
        )
        mail.send(msg)
        flash('Thanks for reaching out! Our team will get back to you shortly.', 'success')
        return redirect(url_for('auth.contact'))

    return render_template('contact.html', form=form)


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
            f'Student registered (pending approval): {user.full_name} ({user.student_id}). Card: {card_number}',
            target_table='users',
            target_id=user.user_id,
            actor_id=user.user_id,
        )
        notify_admins_of_pending_registration(user)

        flash(
            'Registration successful! Your account is pending approval by library staff. '
            'You will be able to log in once approved.',
            'info',
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Contact the library.', 'danger')
                return render_template('auth/login.html', form=form)
            if user.approval_status == 'pending':
                flash('Your account is still pending approval by library staff.', 'warning')
                return render_template('auth/login.html', form=form)
            if user.approval_status == 'rejected':
                flash('Your registration was not approved. Contact the library for details.', 'danger')
                return render_template('auth/login.html', form=form)
            login_user(user)
            log_action('LOGIN', f'User logged in: {user.email}', actor_id=user.user_id)
            next_page = url_for('auth.index')
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(next_page)
        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log_action('LOGOUT', f'User logged out: {current_user.email}')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


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
            db.session.commit()

            print(f'[DEV] Temp password for {user.email}: {temp_password}')

            msg = Message(
                subject='Your ULMS Temporary Password',
                recipients=[user.email],
                body=(
                    f'Hello {user.full_name},\n\n'
                    f'A password reset was requested for your account.\n'
                    f'Your temporary password is: {temp_password}\n\n'
                    f'Please log in and change your password as soon as possible.\n\n'
                    f'If you did not request this, please contact a librarian immediately.'
                ),
            )
            mail.send(msg)

            log_action(
                'PASSWORD_RESET',
                f'Temporary password issued for {user.email}',
                target_table='users',
                target_id=user.user_id,
            )

        flash('If that email is registered, a temporary password has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)
