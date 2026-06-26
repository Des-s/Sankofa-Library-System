from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not current_user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                from app.utils.helpers import log_action
                log_action(
                    'ACCESS_DENIED',
                    f'User {current_user.email} attempted unauthorized access to {f.__name__}',
                )
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def student_required(f):
    return role_required('student')(f)


def librarian_required(f):
    return role_required('librarian', 'admin')(f)


def admin_required(f):
    return role_required('admin')(f)
