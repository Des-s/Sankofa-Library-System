from datetime import date, timedelta

from flask_mail import Message

from app.extensions import mail
from app.models import Checkout, User
from app.utils.helpers import log_action

REMINDER_DAYS_BEFORE_DUE = 2


def send_due_soon_reminders():
    """Email students whose active checkouts are due in REMINDER_DAYS_BEFORE_DUE days."""
    target_date = date.today() + timedelta(days=REMINDER_DAYS_BEFORE_DUE)
    due_soon = Checkout.query.filter(
        Checkout.status == 'active',
        Checkout.expected_return_date == target_date,
    ).all()

    sent = 0
    for checkout in due_soon:
        student = checkout.student
        if not student.email_notifications:
            continue

        msg = Message(
            subject='Reminder: Book Due Soon — Sankofa Library',
            recipients=[student.email],
            body=(
                f'Hello {student.full_name},\n\n'
                f'Your borrowed book "{checkout.book.title}" is due on {checkout.expected_return_date}.\n'
                f'Please return it on time to avoid a fine.\n\n'
                f'Thank you for using Sankofa Library.'
            ),
        )
        mail.send(msg)
        print(f'[DEV] Due-soon reminder sent to {student.email} for "{checkout.book.title}"')
        sent += 1

    if sent:
        log_action('DUE_SOON_REMINDERS', f'Sent {sent} due-soon reminder email(s)')
    return sent


def send_overdue_digest_to_librarians():
    """Email a daily digest of overdue checkouts to librarians who want it."""
    overdue = Checkout.query.filter(Checkout.status == 'overdue').all()
    if not overdue:
        return 0

    librarians = User.query.filter(
        User.role.in_(['librarian', 'admin']),
        User.email_notifications == True,  # noqa: E712
        User.is_active == True,  # noqa: E712
    ).all()

    lines = [f'- "{c.book.title}" — {c.student.full_name} ({c.student.student_id}), due {c.expected_return_date}' for c in overdue]
    body = 'The following books are overdue:\n\n' + '\n'.join(lines)

    sent = 0
    for librarian in librarians:
        msg = Message(subject=f'Overdue Books Digest ({len(overdue)}) — Sankofa Library', recipients=[librarian.email], body=body)
        mail.send(msg)
        print(f'[DEV] Overdue digest sent to {librarian.email}')
        sent += 1

    if sent:
        log_action('OVERDUE_DIGEST', f'Sent overdue digest ({len(overdue)} books) to {sent} staff member(s)')
    return sent


def notify_admins_of_pending_registration(user):
    """Email admins who want notifications that a new student is awaiting approval."""
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
                f'{user.full_name} ({user.student_id}, {user.email}) has registered and is awaiting approval.\n'
                f'Review it from Student Lookup > Pending Approval.'
            ),
        )
        mail.send(msg)
        print(f'[DEV] Pending-registration notice sent to {admin.email}')
