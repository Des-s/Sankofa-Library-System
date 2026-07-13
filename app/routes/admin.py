from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.extensions import db
from app.forms import (
    ChangePasswordForm, LanguageForm, NotificationSettingsForm, ProfilePhotoForm,
    SupportRequestForm, SystemSettingsForm, ThemeForm, UserForm,
)
from app.models import AuditLog, Book, Checkout, Fine, LibraryCard, ReadingSession, Report, SystemSetting, User
from app.utils.decorators import admin_required
from app.utils.helpers import (
    generate_library_card_number, get_book_availability_rate, get_checkouts_by_department,
    get_digital_coverage_rate, get_fine_collection_rate, get_on_time_return_rate,
    get_user_signups_by_month, init_default_settings, log_action, save_profile_photo,
)

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
        'pending_approvals': User.query.filter_by(role='student', approval_status='pending').count(),
    }

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_checkouts = Checkout.query.filter(Checkout.checkout_date >= thirty_days_ago.date()).count()
    monthly_reading = ReadingSession.query.filter(ReadingSession.session_start >= thirty_days_ago).count()
    fine_revenue = db.session.query(func.sum(Fine.total_amount)).filter(Fine.status == 'paid').scalar() or 0

    popular_books = db.session.query(
        Book.title, func.count(Checkout.checkout_id).label('borrow_count')
    ).join(Checkout).group_by(Book.book_id).order_by(func.count(Checkout.checkout_id).desc()).limit(10).all()

    department_breakdown = get_checkouts_by_department()
    signups_by_month = get_user_signups_by_month()

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        monthly_checkouts=monthly_checkouts,
        monthly_reading=monthly_reading,
        fine_revenue=fine_revenue,
        popular_books=popular_books,
        department_breakdown=department_breakdown,
        signups_by_month=signups_by_month,
        book_availability_rate=get_book_availability_rate(),
        on_time_return_rate=get_on_time_return_rate(),
        digital_coverage_rate=get_digital_coverage_rate(),
        fine_collection_rate=get_fine_collection_rate(),
    )


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


@admin_bp.route('/users/<int:user_id>')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    reports_list = Report.query.filter_by(student_id=user_id).order_by(Report.date_filed.desc()).all()
    return render_template('admin/user_detail.html', user=user, reports=reports_list)


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


@admin_bp.route('/profile')
def profile():
    password_form = ChangePasswordForm()
    photo_form = ProfilePhotoForm()
    return render_template('admin/profile.html', password_form=password_form, photo_form=photo_form)


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    init_default_settings()
    form = SystemSettingsForm()
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

    notification_form = NotificationSettingsForm(email_notifications=current_user.email_notifications)
    theme_form = ThemeForm(dark_mode=(current_user.theme_preference == 'dark'))
    language_form = LanguageForm(language_preference=current_user.language_preference)
    support_form = SupportRequestForm()

    return render_template(
        'admin/settings.html',
        form=form,
        notification_form=notification_form,
        theme_form=theme_form,
        language_form=language_form,
        support_form=support_form,
    )


@admin_bp.route('/profile/password', methods=['POST'])
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
    return redirect(url_for('admin.profile'))


@admin_bp.route('/profile/photo', methods=['POST'])
def update_photo():
    photo_form = ProfilePhotoForm()
    if photo_form.validate_on_submit():
        save_profile_photo(current_user, photo_form.profile_photo.data)
        db.session.commit()
        flash('Profile photo updated.', 'success')
    return redirect(url_for('admin.profile'))


@admin_bp.route('/settings/notifications', methods=['POST'])
def update_notifications():
    notification_form = NotificationSettingsForm()
    if notification_form.validate_on_submit():
        current_user.email_notifications = notification_form.email_notifications.data
        db.session.commit()
        flash('Notification preferences saved.', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/theme', methods=['POST'])
def update_theme():
    theme_form = ThemeForm()
    if theme_form.validate_on_submit():
        current_user.theme_preference = 'dark' if theme_form.dark_mode.data else 'light'
        db.session.commit()
        flash('Appearance updated.', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/language', methods=['POST'])
def update_language():
    language_form = LanguageForm()
    if language_form.validate_on_submit():
        current_user.language_preference = language_form.language_preference.data
        db.session.commit()
        flash('Language updated.', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/support', methods=['POST'])
def submit_support_request():
    support_form = SupportRequestForm()
    if support_form.validate_on_submit():
        report = Report(
            report_type='support',
            title=support_form.subject.data.strip(),
            description=support_form.description.data.strip(),
            filed_by=current_user.user_id,
        )
        db.session.add(report)
        db.session.commit()
        log_action('SUPPORT_REQUEST', f'Support request filed: {report.title}', target_table='reports', target_id=report.id)
        flash('Your report has been submitted.', 'success')
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


@admin_bp.route('/reports')
def reports():
    return redirect(url_for('librarian.reports'))
