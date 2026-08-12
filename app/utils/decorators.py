"""Role-based access decorators — faithful port of src/middleware.ts +
src/lib/api-auth.ts requireUser(req, [...roles]).

Notable rules:
- role_required(*roles): redirects to /login if unauthenticated, flashes
  + 403 if the role doesn't match. Logs ACCESS_DENIED.
- student_required: only 'student'.
- librarian_required: 'librarian' OR 'admin' (admin is admitted to all
  librarian routes — mirrors Next.js src/middleware.ts).
- admin_required: only 'admin'.
"""
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """Require that the current user has one of ``roles``.

    Unauthenticated → redirect to /login.
    Inactive account → flash + redirect to /login.
    Wrong role → log ACCESS_DENIED + 403.
    """
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
                    f'User {current_user.email} attempted unauthorized '
                    f'access to {f.__name__}',
                )
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def student_required(f):
    """Only students may access this route."""
    return role_required('student')(f)


def librarian_required(f):
    """Librarians AND admins may access this route (admin admits)."""
    return role_required('librarian', 'admin')(f)


def admin_required(f):
    """Only admins may access this route."""
    return role_required('admin')(f)


def log_action_decorator(action_type, description_template, target_table=None):
    """Decorator that wraps a route and logs an action after it runs.

    ``description_template`` is a format string with access to the route's
    kwargs, e.g. ``'Approved user #{user_id}'``.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            result = f(*args, **kwargs)
            try:
                description = description_template.format(**kwargs)
            except (KeyError, IndexError):
                description = description_template
            from app.utils.helpers import log_action
            log_action(action_type, description, target_table=target_table)
            return result
        return wrapped
    return decorator
