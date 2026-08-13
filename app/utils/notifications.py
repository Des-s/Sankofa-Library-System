"""Email notification helpers.

Every mail.send() is wrapped in _safe_send() catching SMTPException /
OSError. Uses app.logger instead of print(). Null-checks for orphaned
Checkout → Student / Book records.

Functions:
- send_due_soon_reminders: emails students whose active checkouts are
  due in REMINDER_DAYS_BEFORE_DUE days (default 2).
- send_overdue_digest_to_librarians: daily digest of overdue checkouts
  to librarians who want it.
- notify_admins_of_pending_registration: alerts admins who want
  notifications that a new student is awaiting approval.
"""
from datetime import date, timedelta
from smtplib import SMTPException

from flask import current_app
from flask_mail import Message

from app.extensions import mail
from app.models import Checkout, User
from app.utils.helpers import log_action


REMINDER_DAYS_BEFORE_DUE = 2


def _safe_send(message):
    """Send an email, log on failure, never raise."""
    try:
        mail.send(message)
        return True
    except (SMTPException, OSError) as exc:
        current_app.logger.error(
            'notifications: failed to send to %r: %s',
            getattr(message, 'recipients', []), exc,
        )
        return False
    except Exception as exc:  # pragma: no cover - safety net
        current_app.logger.error('notifications: unexpected send error: %s', exc)
        return False


def send_due_soon_reminders():
    """Email students whose active checkouts are due in
    REMINDER_DAYS_BEFORE_DUE days.
    """
    target_date = date.today() + timedelta(days=REMINDER_DAYS_BEFORE_DUE)
    due_soon = Checkout.query.filter(
        Checkout.status == 'active',
        Checkout.expected_return_date == target_date,
    ).all()

    sent = 0
    for checkout in due_soon:
        # Null-check: orphaned checkout or missing book/student.
        student = getattr(checkout, 'student', None)
        book = getattr(checkout, 'book', None)
        if student is None or book is None:
            current_app.logger.warning(
                'send_due_soon_reminders: skipping orphan checkout #%s',
                checkout.checkout_id,
            )
            continue
        if not student.email_notifications:
            continue

        msg = Message(
            subject='Reminder: Book Due Soon — Sankofa Library',
            recipients=[student.email],
            body=(
                f'Hello {student.full_name},\n\n'
                f'Your borrowed book "{book.title}" is due on '
                f'{checkout.expected_return_date}.\n'
                f'Please return it on time to avoid a fine.\n\n'
                f'Thank you for using Sankofa Library.'
            ),
        )
        if _safe_send(msg):
            current_app.logger.info(
                'send_due_soon_reminders: reminder sent to %s for "%s"',
                student.email, book.title,
            )
            sent += 1

    if sent:
        log_action('DUE_SOON_REMINDERS', f'Sent {sent} due-soon reminder email(s)')
    return sent


def send_overdue_digest_to_librarians():
    """Email a daily digest of overdue checkouts to librarians who want it."""
    overdue = Checkout.query.filter(Checkout.status == 'overdue').all()
    if not overdue:
        return 0

    # Filter out orphaned records up front.
    valid_lines = []
    for c in overdue:
        student = getattr(c, 'student', None)
        book = getattr(c, 'book', None)
        if student is None or book is None:
            current_app.logger.warning(
                'send_overdue_digest_to_librarians: skipping orphan checkout #%s',
                c.checkout_id,
            )
            continue
        valid_lines.append(
            f'- "{book.title}" — {student.full_name} ({student.student_id}), '
            f'due {c.expected_return_date}'
        )
    if not valid_lines:
        return 0

    body = 'The following books are overdue:\n\n' + '\n'.join(valid_lines)

    librarians = User.query.filter(
        User.role.in_(['librarian', 'admin']),
        User.email_notifications == True,  # noqa: E712
        User.is_active == True,  # noqa: E712
    ).all()

    sent = 0
    for librarian in librarians:
        msg = Message(
            subject=f'Overdue Books Digest ({len(valid_lines)}) — Sankofa Library',
            recipients=[librarian.email],
            body=body,
        )
        if _safe_send(msg):
            current_app.logger.info(
                'send_overdue_digest_to_librarians: digest sent to %s',
                librarian.email,
            )
            sent += 1

    if sent:
        log_action(
            'OVERDUE_DIGEST',
            f'Sent overdue digest ({len(valid_lines)} books) to '
            f'{sent} staff member(s)',
        )
    return sent


def notify_admins_of_pending_registration(user):
    """Email admins who want notifications that a new student is awaiting approval."""
    if user is None:
        return
    admins = User.query.filter(
        User.role == 'admin',
        User.email_notifications == True,  # noqa: E712
        User.is_active == True,  # noqa: E712
    ).all()
    for admin in admins:
        msg = Message(
            subject='New Student Registration Pending Approval — Sankofa Library',
            recipients=[admin.email],
            body=(
                f'{user.full_name} ({user.student_id}, {user.email}) has '
                f'registered and is awaiting approval.\n'
                f'Review it from Student Lookup > Pending Approval.'
            ),
        )
        if _safe_send(msg):
            current_app.logger.info(
                'notify_admins_of_pending_registration: notice sent to %s',
                admin.email,
            )
