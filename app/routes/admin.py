from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.extensions import db
from app.forms import ChangePasswordForm, SystemSettingsForm, UserForm
from app.models import AuditLog, Book, Checkout, Fine, LibraryCard, ReadingSession, SystemSetting, User
from app.utils.decorators import admin_required
from app.utils.helpers import generate_library_card_number, init_default_settings, log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
@admin_required
def before_request():
    pass


@admin_bp.route('/dashboard')
def dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role='student').count(),
        'active_books': Book.query.filter_by(is_active=True).count(),
        'active_checkouts': Checkout.query.filter(Checkout.status.in_(['active', 'overdue'])).count(),
        'outstanding_fines': db.session.query(func.sum(Fine.total_amount)).filter(
            Fine.status.in_(['issued', 'pending'])
        ).scalar() or 0,
        'reading_sessions': ReadingSession.query.filter(
                               db.func.date(ReadingSession.session_start) == date.today()
                            ).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/users')
def users():
    q = request.args.get('q', '').strip()
    role = request.args.get('role', '')
    query = User.query
    if q:
        query = query.filter(or_(
            User.full_name.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%'),
            User.student_id.ilike(f'%{q}%'),
        ))
    if role:
        query = query.filter_by(role=role)
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(User.full_name).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=pagination.items, pagination=pagination, q=q, role=role)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def user_form(user_id=None):
    user = User.query.get(user_id) if user_id else None
    form = UserForm(obj=user)

    if form.validate_on_submit():
        if user is None:
            existing = User.query.filter_by(email=form.email.data.strip().lower()).first()
            if existing:
                flash('Email already registered.', 'danger')
                return render_template('admin/user_form.html', form=form, user=user)
            if not form.password.data:
                flash('Password is required for new users.', 'danger')
                return render_template('admin/user_form.html', form=form, user=user)

            user = User(
                full_name=form.name.data.strip(),
                email=form.email.data.strip().lower(),
                role=form.role.data,
                student_id=form.student_id.data.strip().upper() if form.student_id.data else None,
                department=form.department.data.strip() if form.department.data else None,
                year_of_study=form.year_of_study.data,
                is_active=form.is_active.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()

            if user.role == 'student' and user.student_id:
                card_number = generate_library_card_number(user.student_id)
                db.session.add(LibraryCard(user_id=user.user_id, card_number=card_number))

            db.session.commit()
            log_action('USER_CREATE', f'User created: {user.email} ({user.role})', target_table='users', target_id=user.user_id)
            flash('User created successfully.', 'success')
        else:
            user.full_name = form.name.data.strip()
            user.email = form.email.data.strip().lower()
            user.role = form.role.data
            user.is_active = form.is_active.data
            if form.password.data:
                user.set_password(form.password.data)
            if user.role == 'student':
                user.department = form.department.data.strip() if form.department.data else None
                user.year_of_study = form.year_of_study.data
            db.session.commit()
            log_action('USER_UPDATE', f'User updated: {user.email}', target_table='users', target_id=user.user_id)
            flash('User updated successfully.', 'success')

        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, user=user)


@admin_bp.route('/users/toggle/<int:user_id>', methods=['POST'])
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.user_id == current_user.user_id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    log_action('USER_TOGGLE', f'User {user.email} {status}', target_table='users', target_id=user_id)
    flash(f'User {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    init_default_settings()
    form = SystemSettingsForm()
    password_form = ChangePasswordForm()
    if request.method == 'GET':
        form.fine_rate_per_day.data = float(db.session.query(SystemSetting).filter_by(setting_key='fine_rate_per_day').first().setting_value)
        form.loan_period_days.data = int(db.session.query(SystemSetting).filter_by(setting_key='loan_period_days').first().setting_value)
        form.library_card_format.data = db.session.query(SystemSetting).filter_by(setting_key='library_card_format').first().setting_value
        form.max_active_checkouts.data = int(db.session.query(SystemSetting).filter_by(setting_key='max_active_checkouts').first().setting_value)

    if form.validate_on_submit():
        for key, value in [
            ('fine_rate_per_day', str(form.fine_rate_per_day.data)),
            ('loan_period_days', str(form.loan_period_days.data)),
            ('library_card_format', form.library_card_format.data.strip()),
            ('max_active_checkouts', str(form.max_active_checkouts.data)),
        ]:
            setting = SystemSetting.query.filter_by(setting_key=key).first()
            if setting:
                setting.setting_value = value
        db.session.commit()
        log_action('SETTINGS_UPDATE', 'System settings updated')
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', form=form, password_form=password_form)


@admin_bp.route('/settings/password', methods=['POST'])
def change_password():
    password_form = ChangePasswordForm()
    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            log_action('PASSWORD_CHANGE', f'Admin changed their own password: {current_user.email}')
            flash('Password updated successfully.', 'success')
    else:
        for errors in password_form.errors.values():
            for error in errors:
                flash(error, 'danger')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/audit')
def audit():
    q = request.args.get('q', '').strip()
    query = AuditLog.query
    if q:
        query = query.filter(or_(
            AuditLog.action_type.ilike(f'%{q}%'),
            AuditLog.description.ilike(f'%{q}%'),
        ))
    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('admin/audit.html', logs=logs, q=q)


@admin_bp.route('/analytics')
def analytics():
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_checkouts = Checkout.query.filter(Checkout.checkout_date >= thirty_days_ago.date()).count()
    monthly_reading = ReadingSession.query.filter(ReadingSession.session_start >= thirty_days_ago).count()
    fine_revenue = db.session.query(func.sum(Fine.total_amount)).filter(Fine.status == 'paid').scalar() or 0

    popular_books = db.session.query(
        Book.title, func.count(Checkout.checkout_id).label('borrow_count')
    ).join(Checkout).group_by(Book.book_id).order_by(func.count(Checkout.checkout_id).desc()).limit(10).all()

    popular_reads = db.session.query(
        Book.title, func.count(ReadingSession.session_id).label('read_count')
    ).join(ReadingSession).group_by(Book.book_id).order_by(func.count(ReadingSession.session_id).desc()).limit(10).all()

    return render_template(
        'admin/analytics.html',
        monthly_checkouts=monthly_checkouts,
        monthly_reading=monthly_reading,
        fine_revenue=fine_revenue,
        popular_books=popular_books,
        popular_reads=popular_reads,
    )


@admin_bp.route('/reports')
def reports():
    return redirect(url_for('librarian.reports'))
