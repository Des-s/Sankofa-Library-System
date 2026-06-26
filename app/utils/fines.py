from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import Checkout, Fine
from app.utils.helpers import get_fine_rate, log_action


def calculate_fine(checkout, return_date=None):
    """Calculate fine for a checkout based on return date."""
    return_date = return_date or date.today()
    if return_date <= checkout.expected_return_date:
        return None

    days_overdue = (return_date - checkout.expected_return_date).days
    rate = get_fine_rate()
    total = Decimal(days_overdue) * rate
    return {
        'days_overdue': days_overdue,
        'amount_per_day': rate,
        'total_amount': total,
    }


def process_return(checkout, librarian, return_date=None):
    """Process a book return and create fine if overdue."""
    return_date = return_date or date.today()
    checkout.actual_return_date = return_date
    checkout.status = 'returned'

    book = checkout.book
    book.available_physical_copies += 1

    fine_data = calculate_fine(checkout, return_date)
    fine = None
    if fine_data:
        fine = Fine(
            checkout_id=checkout.checkout_id,
            user_id=checkout.user_id,
            days_overdue=fine_data['days_overdue'],
            amount_per_day=fine_data['amount_per_day'],
            total_amount=fine_data['total_amount'],
            status='issued',
        )
        db.session.add(fine)

    db.session.commit()

    log_action(
        'RETURN',
        f'Book "{book.title}" returned by user #{checkout.user_id}. '
        + (f'Fine issued: GHS {fine_data["total_amount"]}' if fine_data else 'No fine.'),
        target_table='checkouts',
        target_id=checkout.checkout_id,
        actor_id=librarian.user_id,
    )
    return fine


def update_overdue_statuses():
    """Mark active checkouts as overdue when past due date."""
    today = date.today()
    overdue = Checkout.query.filter(
        Checkout.status == 'active',
        Checkout.expected_return_date < today,
    ).all()
    for checkout in overdue:
        checkout.status = 'overdue'
    if overdue:
        db.session.commit()
    return len(overdue)


def get_accrued_fine_amount(checkout):
    """Calculate current accrued fine for an overdue checkout not yet returned."""
    if checkout.status not in ('active', 'overdue'):
        return Decimal('0.00')
    fine_data = calculate_fine(checkout)
    if fine_data:
        return fine_data['total_amount']
    return Decimal('0.00')
