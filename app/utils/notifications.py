from datetime import date, timedelta

from flask_mail import Message

from app.extensions import mail
from app.models import Checkout
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
