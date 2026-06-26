"""Seed the database with sample data for development and testing."""

from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import Book, Checkout, LibraryCard, User
from app.utils.helpers import generate_library_card_number, init_default_settings


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        init_default_settings()

        admin = User(
            full_name='System Administrator',
            email='admin@sankofa.edu',
            role='admin',
            is_active=True,
        )
        admin.set_password('admin12345')
        db.session.add(admin)

        librarian = User(
            full_name='Jane Librarian',
            email='librarian@sankofa.edu',
            role='librarian',
            is_active=True,
        )
        librarian.set_password('librarian123')
        db.session.add(librarian)

        students = []
        for i, (name, sid, dept, year) in enumerate([
            ('Kwame Mensah', 'STU2024001', 'Computer Science', 2),
            ('Ama Osei', 'STU2024002', 'English Literature', 3),
            ('Kofi Asante', 'STU2024003', 'Mathematics', 1),
        ], start=1):
            s = User(
                student_id=sid,
                full_name=name,
                email=f'student{i}@sankofa.edu',
                role='student',
                department=dept,
                year_of_study=year,
                is_active=True,
            )
            s.set_password('student123')
            db.session.add(s)
            students.append(s)

        db.session.flush()

        for s in students:
            db.session.add(LibraryCard(
                user_id=s.user_id,
                card_number=generate_library_card_number(s.student_id),
            ))

        books_data = [
            ('Introduction to Python Programming', 'Eric Matthes', '978-1593279288', 'No Starch Press', 2019, 'Technology', 5),
            ('Things Fall Apart', 'Chinua Achebe', '978-0385474542', 'Anchor', 1994, 'Literature', 3),
            ('Clean Code', 'Robert C. Martin', '978-0132350884', 'Prentice Hall', 2008, 'Technology', 2),
            ('The Republic', 'Plato', '978-0140449143', 'Penguin Classics', 2007, 'Philosophy', 4),
            ('A Brief History of Time', 'Stephen Hawking', '978-0553380163', 'Bantam', 1998, 'Science', 2),
        ]

        books = []
        for title, author, isbn, pub, year, cat, copies in books_data:
            b = Book(
                title=title,
                author=author,
                isbn=isbn,
                publisher=pub,
                year_published=year,
                category=cat,
                total_physical_copies=copies,
                available_physical_copies=copies,
                has_digital=True,
                is_active=True,
            )
            db.session.add(b)
            books.append(b)

        db.session.flush()

        uploads_dir = app.config['UPLOAD_FOLDER']
        import os
        os.makedirs(uploads_dir, exist_ok=True)

        sample_content = """SANKOFA LIBRARY SYSTEM - SAMPLE DIGITAL BOOK
============================================

This is a sample digital book for demonstration purposes.
In production, upload PDF or HTML files for each book.

Chapter 1: Introduction
-----------------------
Welcome to the Sankofa Library online reading portal.
Your library card verification ensures secure access to digital resources.

Chapter 2: Reading Online
-------------------------
After verifying your library card, you can read books directly in your browser.
All reading sessions are logged for audit purposes.
"""
        for b in books[:3]:
            filepath = os.path.join(uploads_dir, f'book_{b.book_id}_{b.isbn.replace("-", "")}.txt')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sample_content.replace('SANKOFA LIBRARY SYSTEM', b.title.upper()))
            b.digital_file_path = filepath

        db.session.flush()

        checkout = Checkout(
            user_id=students[0].user_id,
            book_id=books[1].book_id,
            librarian_id=librarian.user_id,
            checkout_date=date.today() - timedelta(days=20),
            expected_return_date=date.today() - timedelta(days=6),
            status='overdue',
        )
        books[1].available_physical_copies -= 1
        db.session.add(checkout)

        db.session.commit()

        print('Database seeded successfully!')
        print('\n--- Login Credentials ---')
        print('Admin:     admin@sankofa.edu / admin12345')
        print('Librarian: librarian@sankofa.edu / librarian123')
        print('Students:  student1@sankofa.edu / student123 (and student2, student3)')
        print('\n--- Library Cards ---')
        for s in students:
            print(f'  {s.full_name}: {s.library_card.card_number}')


if __name__ == '__main__':
    seed()
