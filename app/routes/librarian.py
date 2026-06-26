from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename
import os

from app.extensions import db
from app.forms import BookForm, CheckoutForm, FineActionForm, ReturnForm
from app.models import Book, Checkout, Fine, User
from app.utils.decorators import librarian_required
from app.utils.fines import get_accrued_fine_amount, process_return, update_overdue_statuses
from app.utils.helpers import get_loan_period_days, log_action
from flask import current_app

librarian_bp = Blueprint('librarian', __name__, url_prefix='/librarian')


@librarian_bp.before_request
@login_required
@librarian_required
def before_request():
    update_overdue_statuses()


@librarian_bp.route('/dashboard')
def dashboard():
    today = date.today()
    checked_out_today = Checkout.query.filter(Checkout.checkout_date == today).count()
    overdue_count = Checkout.query.filter(Checkout.status == 'overdue').count()
    recent_checkouts = Checkout.query.order_by(Checkout.created_at.desc()).limit(10).all()
    return render_template(
        'librarian/dashboard.html',
        checked_out_today=checked_out_today,
        overdue_count=overdue_count,
        recent_checkouts=recent_checkouts,
    )


@librarian_bp.route('/students')
def students():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='student')
    if q:
        query = query.filter(or_(
            User.student_id.ilike(f'%{q}%'),
            User.full_name.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%'),
        ))
    students_list = query.order_by(User.full_name).all()
    return render_template('librarian/students.html', students=students_list, q=q)


@librarian_bp.route('/students/<int:user_id>')
def student_detail(user_id):
    student = User.query.filter_by(user_id=user_id, role='student').first_or_404()
    checkouts = Checkout.query.filter_by(user_id=user_id).order_by(Checkout.checkout_date.desc()).all()
    fines_list = Fine.query.filter_by(user_id=user_id).order_by(Fine.created_at.desc()).all()
    return render_template('librarian/student_detail.html', student=student, checkouts=checkouts, fines=fines_list)


@librarian_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    form = CheckoutForm()
    form.book_id.choices = [
        (b.book_id, f'{b.title} by {b.author} ({b.available_physical_copies} available)')
        for b in Book.query.filter(Book.is_active == True, Book.available_physical_copies > 0).order_by(Book.title).all()
    ]

    student = None
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            form.student_search.data = q
            student = User.query.filter(
                User.role == 'student',
                or_(User.student_id.ilike(q), User.full_name.ilike(f'%{q}%')),
            ).first()

    if form.validate_on_submit():
        search = form.student_search.data.strip()
        student = User.query.filter(
            User.role == 'student',
            or_(User.student_id.ilike(search), User.full_name.ilike(f'%{search}%')),
        ).first()
        if not student:
            flash('Student not found.', 'danger')
            return render_template('librarian/checkout.html', form=form, student=student)

        book = Book.query.get(form.book_id.data)
        if not book or book.available_physical_copies <= 0:
            flash('Book is not available for checkout.', 'danger')
            return render_template('librarian/checkout.html', form=form, student=student)

        loan_days = get_loan_period_days()
        checkout_date = date.today()
        checkout_record = Checkout(
            user_id=student.user_id,
            book_id=book.book_id,
            librarian_id=current_user.user_id,
            checkout_date=checkout_date,
            expected_return_date=checkout_date + timedelta(days=loan_days),
            status='active',
        )
        book.available_physical_copies -= 1
        db.session.add(checkout_record)
        db.session.commit()

        log_action(
            'CHECKOUT',
            f'"{book.title}" checked out to {student.full_name} ({student.student_id})',
            target_table='checkouts',
            target_id=checkout_record.checkout_id,
        )
        flash(f'Book "{book.title}" checked out to {student.full_name}. Due: {checkout_record.expected_return_date}.', 'success')
        return redirect(url_for('librarian.checkout'))

    return render_template('librarian/checkout.html', form=form, student=student)


@librarian_bp.route('/return', methods=['GET', 'POST'])
def return_book():
    active = Checkout.query.filter(Checkout.status.in_(['active', 'overdue'])).all()
    form = ReturnForm()
    form.checkout_id.choices = [
        (c.checkout_id, f'{c.student.full_name} — {c.book.title} (due {c.expected_return_date})')
        for c in active
    ]

    if form.validate_on_submit():
        checkout = Checkout.query.get(form.checkout_id.data)
        if not checkout or checkout.status not in ('active', 'overdue'):
            flash('Invalid checkout record.', 'danger')
        else:
            fine = process_return(checkout, current_user)
            if fine:
                flash(f'Book returned. Fine issued: GHS {fine.total_amount} ({fine.days_overdue} days overdue).', 'warning')
            else:
                flash('Book returned successfully. No fine.', 'success')
            return redirect(url_for('librarian.return_book'))

    return render_template('librarian/return.html', form=form)


@librarian_bp.route('/overdue')
def overdue():
    overdue_list = Checkout.query.filter_by(status='overdue').order_by(Checkout.expected_return_date).all()
    accrued = {c.checkout_id: get_accrued_fine_amount(c) for c in overdue_list}
    return render_template('librarian/overdue.html', checkouts=overdue_list, accrued=accrued)


@librarian_bp.route('/fines', methods=['GET', 'POST'])
def fines():
    form = FineActionForm()
    if form.validate_on_submit():
        fine = Fine.query.get(form.fine_id.data)
        if not fine:
            flash('Fine not found.', 'danger')
        elif form.action.data == 'waived':
            if not form.waiver_reason.data:
                flash('A reason is required to waive a fine.', 'danger')
            else:
                fine.status = 'waived'
                fine.waiver_reason = form.waiver_reason.data
                fine.processed_by = current_user.user_id
                db.session.commit()
                log_action('FINE_WAIVED', f'Fine #{fine.fine_id} waived: {form.waiver_reason.data}', target_table='fines', target_id=fine.fine_id)
                flash('Fine waived.', 'success')
        elif form.action.data == 'paid':
            fine.status = 'paid'
            fine.processed_by = current_user.user_id
            db.session.commit()
            log_action('FINE_PAID', f'Fine #{fine.fine_id} marked as paid', target_table='fines', target_id=fine.fine_id)
            flash('Fine marked as paid.', 'success')
        return redirect(url_for('librarian.fines'))

    fines_list = Fine.query.order_by(Fine.created_at.desc()).all()
    return render_template('librarian/fines.html', fines=fines_list, form=form)


@librarian_bp.route('/books', methods=['GET'])
def books():
    q = request.args.get('q', '').strip()
    query = Book.query
    if q:
        query = query.filter(or_(Book.title.ilike(f'%{q}%'), Book.author.ilike(f'%{q}%'), Book.isbn.ilike(f'%{q}%')))
    books_list = query.order_by(Book.title).all()
    return render_template('librarian/books.html', books=books_list, q=q)


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@librarian_bp.route('/books/add', methods=['GET', 'POST'])
@librarian_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
def book_form(book_id=None):
    book = Book.query.get(book_id) if book_id else None
    form = BookForm(obj=book)
    if book:
        form.total_physical_copies.data = book.total_physical_copies

    if form.validate_on_submit():
        if book is None:
            existing = Book.query.filter_by(isbn=form.isbn.data).first()
            if existing:
                flash('A book with this ISBN already exists.', 'danger')
                return render_template('librarian/book_form.html', form=form, book=book)

            book = Book(
                title=form.title.data.strip(),
                author=form.author.data.strip(),
                isbn=form.isbn.data.strip(),
                publisher=form.publisher.data.strip() if form.publisher.data else None,
                year_published=form.year_published.data,
                category=form.category.data.strip() if form.category.data else None,
                total_physical_copies=form.total_physical_copies.data,
                available_physical_copies=form.total_physical_copies.data,
                is_active=form.is_active.data,
            )
            db.session.add(book)
            db.session.flush()
        else:
            checked_out = book.total_physical_copies - book.available_physical_copies
            new_total = form.total_physical_copies.data
            if new_total < checked_out:
                flash(f'Cannot reduce copies below {checked_out} (currently checked out).', 'danger')
                return render_template('librarian/book_form.html', form=form, book=book)
            book.title = form.title.data.strip()
            book.author = form.author.data.strip()
            book.isbn = form.isbn.data.strip()
            book.publisher = form.publisher.data.strip() if form.publisher.data else None
            book.year_published = form.year_published.data
            book.category = form.category.data.strip() if form.category.data else None
            diff = new_total - book.total_physical_copies
            book.total_physical_copies = new_total
            book.available_physical_copies = max(0, book.available_physical_copies + diff)
            book.is_active = form.is_active.data

        file = form.digital_file.data
        if file and file.filename:
            if _allowed_file(file.filename):
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f'book_{book.book_id or "new"}_{form.isbn.data}.{ext}')
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                book.digital_file_path = filepath
                book.has_digital = True
            else:
                flash('Invalid file type. Allowed: PDF, TXT, HTML.', 'danger')
                return render_template('librarian/book_form.html', form=form, book=book)

        db.session.commit()
        if not book_id:
            log_action('BOOK_CREATE', f'Book added: {book.title}', target_table='books', target_id=book.book_id)
            flash('Book added successfully.', 'success')
        else:
            log_action('BOOK_UPDATE', f'Book updated: {book.title}', target_table='books', target_id=book.book_id)
            flash('Book updated successfully.', 'success')
        return redirect(url_for('librarian.books'))

    return render_template('librarian/book_form.html', form=form, book=book)


@librarian_bp.route('/books/deactivate/<int:book_id>', methods=['POST'])
def deactivate_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_active = False
    db.session.commit()
    log_action('BOOK_DEACTIVATE', f'Book deactivated: {book.title}', target_table='books', target_id=book_id)
    flash('Book deactivated.', 'info')
    return redirect(url_for('librarian.books'))


@librarian_bp.route('/reports')
def reports():
    popular = db.session.query(
        Book.title, func.count(Checkout.checkout_id).label('count')
    ).join(Checkout).group_by(Book.book_id).order_by(func.count(Checkout.checkout_id).desc()).limit(10).all()

    total_fines = db.session.query(func.sum(Fine.total_amount)).filter(Fine.status == 'paid').scalar() or 0
    active_checkouts = Checkout.query.filter(Checkout.status.in_(['active', 'overdue'])).count()
    overdue_count = Checkout.query.filter_by(status='overdue').count()

    return render_template(
        'librarian/reports.html',
        popular=popular,
        total_fines=total_fines,
        active_checkouts=active_checkouts,
        overdue_count=overdue_count,
    )
