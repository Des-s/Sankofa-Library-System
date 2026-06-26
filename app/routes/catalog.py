from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from app.forms import CatalogSearchForm
from app.models import Book

catalog_bp = Blueprint('catalog', __name__)


@catalog_bp.route('/catalog')
@login_required
def catalog():
    form = CatalogSearchForm(request.args, meta={'csrf': False})
    categories = [c[0] for c in Book.query.with_entities(Book.category).distinct().all() if c[0]]
    form.category.choices = [('', 'All Categories')] + [(c, c) for c in sorted(categories)]

    query = Book.query.filter_by(is_active=True)
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    availability = request.args.get('availability', '')

    if q:
        query = query.filter(or_(
            Book.title.ilike(f'%{q}%'),
            Book.author.ilike(f'%{q}%'),
            Book.isbn.ilike(f'%{q}%'),
            Book.category.ilike(f'%{q}%'),
        ))
    if category:
        query = query.filter_by(category=category)
    if availability == 'physical':
        query = query.filter(Book.available_physical_copies > 0)
    elif availability == 'digital':
        query = query.filter_by(has_digital=True)

    books = query.order_by(Book.title).all()
    return render_template('catalog/catalog.html', books=books, form=form, q=q, category=category, availability=availability)


@catalog_bp.route('/catalog/<int:book_id>')
@login_required
def book_detail(book_id):
    book = Book.query.filter_by(book_id=book_id, is_active=True).first_or_404()
    return render_template('catalog/detail.html', book=book)
