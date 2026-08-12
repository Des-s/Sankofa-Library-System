"""Catalog blueprint — public-ish catalog browse + book detail.

Sankofa Library System catalog area (src/app/(app)/catalog/...).
Both routes require @login_required (matches the the design system middleware
gate that redirects unauthenticated users to /login for any /catalog
route).

Routes:
- `/catalog` — browse with search (q), category filter, availability
  filter, sort, paginate 12/page.
- `/catalog/<book_id>` — book detail with related books by category.
"""
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
    categories = [
        c[0] for c in Book.query.with_entities(Book.category).distinct().all()
        if c[0]
    ]
    form.category.choices = [('', 'All Categories')] + [
        (c, c) for c in sorted(categories)
    ]

    query = Book.query.filter_by(is_active=True)
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    availability = request.args.get('availability', '')
    sort = request.args.get('sort', 'title')

    if q:
        query = query.filter(or_(
            Book.title.ilike(f'%{q}%'),
            Book.author.ilike(f'%{q}%'),
            Book.isbn.ilike(f'%{q}%'),
            Book.category.ilike(f'%{q}%'),
        ))
    if category:
        query = query.filter_by(category=category)
    if subcategory:
        query = query.filter_by(subcategory=subcategory)
    if availability == 'physical':
        query = query.filter(Book.available_physical_copies > 0)
    elif availability == 'digital':
        query = query.filter_by(has_digital=True)

    # Sort.
    if sort == 'title_desc':
        query = query.order_by(Book.title.desc())
    elif sort == 'author':
        query = query.order_by(Book.author.asc())
    elif sort == 'year':
        query = query.order_by(Book.year_published.desc().nullslast())
    elif sort == 'recent':
        query = query.order_by(Book.created_at.desc())
    else:  # 'title' default
        query = query.order_by(Book.title.asc())

    subcategories = []
    if category:
        subcategories = [
            s[0] for s in Book.query.with_entities(Book.subcategory)
            .filter(Book.category == category, Book.subcategory.isnot(None))
            .distinct().all()
        ]
        subcategories = sorted(subcategories)

    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    return render_template(
        'catalog/catalog.html',
        books=pagination.items,
        pagination=pagination,
        form=form,
        q=q,
        category=category,
        subcategory=subcategory,
        subcategories=subcategories,
        categories=sorted(categories),
        availability=availability,
        sort=sort,
    )


@catalog_bp.route('/catalog/<int:book_id>')
@login_required
def book_detail(book_id):
    """Full book detail page with metadata, availability, cover, and related
    books by category. (FLASK-ADAPT)
    """
    book = Book.query.filter_by(book_id=book_id, is_active=True).first_or_404()

    related_books = []
    if book.category:
        related_books = (
            Book.query
            .filter(
                Book.is_active.is_(True),
                Book.category == book.category,
                Book.book_id != book.book_id,
            )
            .order_by(Book.title)
            .limit(4)
            .all()
        )

    return render_template(
        'catalog/detail.html', book=book, related_books=related_books,
    )
