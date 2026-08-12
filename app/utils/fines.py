"""Fine calculation + checkout lifecycle helpers.

Faithful port of src/lib/library.ts (calculateFine, processReturn,
updateOverdueStatuses, getAccruedFine).

Notable features (FLASK-ADAPT):
- calculate_fine: returns None if not overdue.
- process_return: double-return guard — no-op if already returned;
  never increments available_physical_copies above total_physical_copies.
- update_overdue_statuses: marks active → overdue, AND refreshes stale
  fines so days_overdue + total_amount stay accurate as time passes.
- get_accrued_fine_amount: live accrual for active/overdue checkouts.
"""
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import Checkout, Fine
from app.utils.helpers import get_fine_rate, log_action


def calculate_fine(checkout, return_date=None):
    """Calculate fine for a checkout based on return date.

    Returns None if not overdue.
    """
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
    """Process a book return and create fine if overdue.

    Includes a double-return guard: if the book has already been returned
    (or its availability count is already at the cap), no increment
    happens and the call is a no-op. (FLASK-ADAPT)
    """
    return_date = return_date or date.today()

    # Double-return guard — only mark returned once.
    if checkout.status == 'returned' or checkout.actual_return_date is not None:
        return None

    book = checkout.book
    # Guard against already-full shelves (idempotent returns).
    if book.available_physical_copies < book.total_physical_copies:
        book.available_physical_copies += 1

    checkout.actual_return_date = return_date
    checkout.status = 'returned'

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
        + (
            f'Fine issued: GHS {fine_data["total_amount"]}'
            if fine_data else 'No fine.'
        ),
        target_table='checkouts',
        target_id=checkout.checkout_id,
        actor_id=librarian.user_id,
    )
    return fine


def update_overdue_statuses():
    """Mark active checkouts as overdue when past due date.

    Also refreshes stale fines: any Fine tied to an active/overdue
    checkout is updated so its `days_overdue` and `total_amount`
    reflect the current date. (FLASK-ADAPT)
    """
    today = date.today()
    overdue = Checkout.query.filter(
        Checkout.status == 'active',
        Checkout.expected_return_date < today,
    ).all()
    for checkout in overdue:
        checkout.status = 'overdue'
    if overdue:
        db.session.commit()

    # Refresh stale fines — keeps them accurate as time passes.
    rate = get_fine_rate()
    stale_fines = (
        Fine.query
        .join(Checkout, Fine.checkout_id == Checkout.checkout_id)
        .filter(Checkout.status.in_(['active', 'overdue']))
        .filter(Fine.status.in_(['issued', 'pending']))
        .all()
    )
    today = date.today()
    for fine in stale_fines:
        checkout = fine.checkout
        if today <= checkout.expected_return_date:
            new_days = 0
            new_total = Decimal('0.00')
        else:
            new_days = (today - checkout.expected_return_date).days
            new_total = Decimal(new_days) * rate
        if new_days != fine.days_overdue or new_total != fine.total_amount:
            fine.days_overdue = new_days
            fine.total_amount = new_total
    if stale_fines:
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
