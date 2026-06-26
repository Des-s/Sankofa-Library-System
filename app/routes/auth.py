import secrets
import string

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message

from app.extensions import db, mail
from app.forms import LoginForm, RegistrationForm
from app.models import LibraryCard, User
from app.utils.helpers import generate_library_card_number, log_action


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_librarian:
            return redirect(url_for('librarian.dashboard'))
        return redirect(url_for('student.dashboard'))
    return render_template('index.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            student_id=form.student_id.data.strip().upper(),
            full_name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role='student',
            department=form.department.data.strip(),
            year_of_study=form.year_of_study.data,
            is_active=True,
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
            f'Student registered: {user.full_name} ({user.student_id}). Card: {card_number}',
            target_table='users',
            target_id=user.user_id,
            actor_id=user.user_id,
        )

        flash(f'Registration successful! Your library card number is: {card_number}', 'success')
        login_user(user)
        return redirect(url_for('student.dashboard'))

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

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
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

    return render_template('auth/forgot_password.html')
