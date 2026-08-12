"""Admin blueprint — /admin/* routes.

All routes require @login_required + @admin_required via before_request.
Faithful port of the Next.js admin area (src/app/(app)/admin/...).

Routes:
- `/dashboard` — 6 stat cards, Chart.js data (user growth, checkout
  volume, category distribution), top 10 borrowed books, recent audit
  logs.
- `/users` — search by name/email/student_id, filter by role, paginate
  12/page.
- `/users/add`, `/users/<id>/edit`, `/users/<id>` — user CRUD + detail.
- `/users/toggle/<id>` — activate/deactivate (POST with CSRF, can't
  deactivate self).
- `/approvals` — list pending students, approve/reject (POST with CSRF).
- `/audit` — searchable audit log, filter by action_type.
- `/settings` — system settings form (fine_rate, loan_period,
  max_checkouts, card_format, email_domain, currency, library_name,
  library_address).
- `/reports` — list all reports.
- `/profile` — change password + profile photo.
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.extensions import db
from app.forms import (
    ChangePasswordForm, LanguageForm, NotificationSettingsForm, ProfilePhotoForm,
    SupportRequestForm, SystemSettingsForm, ThemeForm, UserForm,
)
from app.models import (
    AuditLog, Book, Checkout, Fine, LibraryCard, ReadingSession, Report,
    SystemSetting, User,
)
from app.utils.decorators import admin_required
from app.utils.helpers import (
    generate_library_card_number, get_book_availability_rate,
    get_checkouts_by_department, get_digital_coverage_rate,
    get_fine_collection_rate, get_on_time_return_rate,
    get_user_signups_by_month, init_default_settings, log_action,
    save_profile_photo,
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
@admin_required
def before_request():
    """Every /admin/* route requires an authenticated admin."""
    pass


# ---------------------------------------------------------------------------
# /dashboard — admin overview (mirror src/app/(app)/admin/dashboard/page.tsx)
# ---------------------------------------------------------------------------
@admin_bp.route('/dashboard')
def dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role='student').count(),
        'active_books': Book.query.filter_by(is_active=True).count(),
        'active_checkouts': Checkout.query.filter(
            Checkout.status.in_(['active', 'overdue'])
        ).count(),
        'outstanding_fines': db.session.query(func.sum(Fine.total_amount)).filter(
            Fine.status.in_(['issued', 'pending'])
        ).scalar() or 0,
        'reading_sessions': ReadingSession.query.filter(
            db.func.date(ReadingSession.session_start) == date.today()
        ).count(),
        'pending_approvals': User.query.filter_by(
            role='student', approval_status='pending'
        ).count(),
    }

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_checkouts = Checkout.query.filter(
        Checkout.checkout_date >= thirty_days_ago.date()
    ).count()
    monthly_reading = ReadingSession.query.filter(
        ReadingSession.session_start >= thirty_days_ago
    ).count()
    fine_revenue = (
        db.session.query(func.sum(Fine.total_amount))
        .filter(Fine.status == 'paid').scalar() or 0
    )

    popular_books = (
        db.session.query(
            Book.title, func.count(Checkout.checkout_id).label('borrow_count')
        )
        .join(Checkout)
        .group_by(Book.book_id)
        .order_by(func.count(Checkout.checkout_id).desc())
        .limit(10)
        .all()
    )

    department_breakdown = get_checkouts_by_department()
    signups_by_month = get_user_signups_by_month()

    # ---- Chart.js data (FLASK-ADAPT) ----
    checkout_volume = _get_checkout_volume_by_month(months=6)
    category_distribution = _get_category_distribution()

    # Recent audit logs for the dashboard panel.
    recent_logs = (
        AuditLog.query
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        monthly_checkouts=monthly_checkouts,
        monthly_reading=monthly_reading,
        fine_revenue=fine_revenue,
        popular_books=popular_books,
        department_breakdown=department_breakdown,
        signups_by_month=signups_by_month,
        checkout_volume=checkout_volume,
        category_distribution=category_distribution,
        recent_logs=recent_logs,
        book_availability_rate=get_book_availability_rate(),
        on_time_return_rate=get_on_time_return_rate(),
        digital_coverage_rate=get_digital_coverage_rate(),
        fine_collection_rate=get_fine_collection_rate(),
    )


def _get_checkout_volume_by_month(months=6):
    """(label, count) tuples of checkouts per month for the last N months."""
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
        count = Checkout.query.filter(
            Checkout.checkout_date >= start,
            Checkout.checkout_date < end,
        ).count()
        buckets.append((start.strftime('%b %Y'), count))
    return buckets


def _get_category_distribution():
    """(label, count) tuples of books per category."""
    rows = (
        db.session.query(Book.category, db.func.count(Book.book_id))
        .filter(Book.is_active.is_(True), Book.category.isnot(None))
        .group_by(Book.category)
        .order_by(db.func.count(Book.book_id).desc())
        .all()
    )
    return [(c or 'Uncategorized', n) for c, n in rows]


# ---------------------------------------------------------------------------
# /users — paginated user list with search + role filter (12/page)
# ---------------------------------------------------------------------------
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
    pagination = query.order_by(User.full_name).paginate(
        page=page, per_page=12, error_out=False,
    )
    return render_template(
        'admin/users.html',
        users=pagination.items, pagination=pagination, q=q, role=role,
    )


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def user_form(user_id=None):
    user = User.query.get(user_id) if user_id else None
    form = UserForm(obj=user)

    if form.validate_on_submit():
        if user is None:
            existing = User.query.filter_by(
                email=form.email.data.strip().lower()
            ).first()
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
                db.session.add(LibraryCard(
                    user_id=user.user_id, card_number=card_number,
                ))

            db.session.commit()
            log_action(
                'USER_CREATE', f'User created: {user.email} ({user.role})',
                target_table='users', target_id=user.user_id,
            )
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
            log_action(
                'USER_UPDATE', f'User updated: {user.email}',
                target_table='users', target_id=user.user_id,
            )
            flash('User updated successfully.', 'success')

        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    reports_list = (
        Report.query.filter_by(student_id=user_id)
        .order_by(Report.date_filed.desc()).all()
    )
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
    log_action(
        'USER_TOGGLE', f'User {user.email} {status}',
        target_table='users', target_id=user_id,
    )
    flash(f'User {status}.', 'success')
    return redirect(url_for('admin.users'))


# ---------------------------------------------------------------------------
# /approvals — list pending students + approve/reject
# ---------------------------------------------------------------------------
@admin_bp.route('/approvals')
def approvals():
    pending_students = (
        User.query
        .filter_by(role='student', approval_status='pending')
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template('librarian/approvals.html', pending_students=pending_students)


@admin_bp.route('/approvals/<int:user_id>/approve', methods=['POST'])
def approve_student(user_id):
    student = User.query.filter_by(user_id=user_id, role='student').first_or_404()
    student.approval_status = 'approved'
    db.session.commit()
    log_action(
        'STUDENT_APPROVE',
        f'Approved student registration: {student.email}',
        target_table='users', target_id=user_id,
        actor_id=current_user.user_id,
    )
    flash(f'{student.full_name} approved.', 'success')
    return redirect(url_for('admin.approvals'))


@admin_bp.route('/approvals/<int:user_id>/reject', methods=['POST'])
def reject_student(user_id):
    student = User.query.filter_by(user_id=user_id, role='student').first_or_404()
    student.approval_status = 'rejected'
    db.session.commit()
    log_action(
        'STUDENT_REJECT',
        f'Rejected student registration: {student.email}',
        target_table='users', target_id=user_id,
        actor_id=current_user.user_id,
    )
    flash(f'{student.full_name} rejected.', 'info')
    return redirect(url_for('admin.approvals'))


# ---------------------------------------------------------------------------
# /audit — searchable audit log with action_type filter
# ---------------------------------------------------------------------------
@admin_bp.route('/audit')
def audit():
    q = request.args.get('q', '').strip()
    action_type = request.args.get('action_type', '').strip()
    target_table = request.args.get('target_table', '').strip()
    query = AuditLog.query
    if q:
        query = query.filter(or_(
            AuditLog.action_type.ilike(f'%{q}%'),
            AuditLog.description.ilike(f'%{q}%'),
        ))
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    if target_table:
        query = query.filter(AuditLog.target_table == target_table)

    # Distinct action types and target tables for the filter dropdowns.
    action_types = [
        row[0] for row in
        db.session.query(AuditLog.action_type).distinct()
        .order_by(AuditLog.action_type).all()
        if row[0]
    ]
    target_tables = [
        row[0] for row in
        db.session.query(AuditLog.target_table)
        .filter(AuditLog.target_table.isnot(None))
        .distinct().order_by(AuditLog.target_table).all()
        if row[0]
    ]

    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False,
    )
    return render_template(
        'admin/audit.html',
        logs=pagination.items, pagination=pagination,
        q=q, action_type=action_type, target_table=target_table,
        action_types=action_types, target_tables=target_tables,
    )


# ---------------------------------------------------------------------------
# /settings — system settings form
# ---------------------------------------------------------------------------
@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    init_default_settings()
    form = SystemSettingsForm()

    setting_keys = [
        'fine_rate_per_day', 'loan_period_days', 'library_card_format',
        'max_active_checkouts', 'student_email_domain', 'currency_symbol',
        'library_name', 'library_address',
    ]

    if request.method == 'GET':
        def _val(key, default):
            s = SystemSetting.query.filter_by(setting_key=key).first()
            return s.setting_value if s else default

        form.fine_rate_per_day.data = float(_val(
            'fine_rate_per_day',
            str(current_app.config.get('DEFAULT_FINE_RATE', 1.00)),
        ))
        form.loan_period_days.data = int(_val(
            'loan_period_days',
            str(current_app.config.get('DEFAULT_LOAN_PERIOD_DAYS', 14)),
        ))
        form.library_card_format.data = _val(
            'library_card_format',
            current_app.config.get('DEFAULT_CARD_FORMAT', 'LIB-{year}-{student_id}'),
        )
        form.max_active_checkouts.data = int(_val(
            'max_active_checkouts',
            str(current_app.config.get('DEFAULT_MAX_ACTIVE_CHECKOUTS', 5)),
        ))
        form.student_email_domain.data = _val(
            'student_email_domain',
            current_app.config.get('DEFAULT_STUDENT_EMAIL_DOMAIN', 'st.knust.edu.gh'),
        )
        form.currency_symbol.data = _val(
            'currency_symbol',
            current_app.config.get('DEFAULT_CURRENCY_SYMBOL', 'GHS'),
        )
        form.library_name.data = _val('library_name', 'Sankofa Academic Library')
        form.library_address.data = _val('library_address', 'Kumasi, Ghana')

    if form.validate_on_submit():
        new_values = {
            'fine_rate_per_day': str(form.fine_rate_per_day.data),
            'loan_period_days': str(form.loan_period_days.data),
            'library_card_format': form.library_card_format.data.strip(),
            'max_active_checkouts': str(form.max_active_checkouts.data),
            'student_email_domain': form.student_email_domain.data.strip().lower(),
            'currency_symbol': form.currency_symbol.data.strip(),
            'library_name': form.library_name.data.strip(),
            'library_address': (
                form.library_address.data.strip()
                if form.library_address.data else ''
            ),
        }
        for key, value in new_values.items():
            setting = SystemSetting.query.filter_by(setting_key=key).first()
            if setting:
                setting.setting_value = value
            else:
                db.session.add(SystemSetting(
                    setting_key=key, setting_value=value,
                ))
        db.session.commit()
        log_action(
            'SETTINGS_UPDATE',
            f'Admin updated system settings: {", ".join(setting_keys)}',
        )
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))

    notification_form = NotificationSettingsForm(
        email_notifications=current_user.email_notifications
    )
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


# ---------------------------------------------------------------------------
# /reports — admin can view all reports via the librarian reports view
# (admin is admitted to librarian routes — see librarian_required).
# ---------------------------------------------------------------------------
@admin_bp.route('/reports')
def reports():
    return redirect(url_for('librarian.reports'))


# ---------------------------------------------------------------------------
# /profile — change password + profile photo
# ---------------------------------------------------------------------------
@admin_bp.route('/profile')
def profile():
    password_form = ChangePasswordForm()
    photo_form = ProfilePhotoForm()
    return render_template(
        'admin/profile.html',
        password_form=password_form, photo_form=photo_form,
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
            log_action(
                'PASSWORD_CHANGE',
                f'Admin changed their own password: {current_user.email}',
            )
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


# ---------------------------------------------------------------------------
# /settings/* — secondary settings forms
# ---------------------------------------------------------------------------
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
        current_user.theme_preference = (
            'dark' if theme_form.dark_mode.data else 'light'
        )
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
        log_action(
            'SUPPORT_REQUEST',
            f'Support request filed: {report.title}',
            target_table='reports', target_id=report.id,
        )
        flash('Your report has been submitted.', 'success')
    return redirect(url_for('admin.settings'))
