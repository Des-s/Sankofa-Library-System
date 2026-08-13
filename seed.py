"""Seed the database with sample data — populates the database with sample data.

Seeds:
- 6 users: admin (Adwoa Boateng), librarian (Kwabena Owusu), 3 approved
  students (Kwame Mensah STU2024001, Ama Osei STU2024002, Kofi Asante
  STU2024003), 1 pending (Akosua Frimpong STU2024004).
- Library cards for all 4 students.
- 15 books (African authors featured: Things Fall Apart, Half of a Yellow
  Sun, Homegoing, Americanah, Sapiens, Clean Code, etc.).
- 5 checkouts (1 overdue, 2 active, 2 returned).
- 1 fine.
- 1 reading session.
- 8 system settings.
- Audit log entries.

Passwords:
- admin@sankofa.edu / admin12345
- librarian@sankofa.edu / librarian123
- kwame.mensah@st.knust.edu.gh / student123
- ama.osei@st.knust.edu.gh / student123
- kofi.asante@st.knust.edu.gh / student123
- akosua.frimpong@st.knust.edu.gh / student123 (pending — cannot log in)
"""
import os
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    AuditLog, Book, Checkout, Fine, LibraryCard, ReadingSession,
    SystemSetting, User,
)
from app.utils.covers import fetch_cover_by_isbn
from app.utils.helpers import (
    generate_library_card_number, init_default_settings,
)


# ---- Books (sample book data) -------------------------
BOOKS_DATA = [
    {
        'title': 'Introduction to Python Programming',
        'author': 'Eric Matthes',
        'isbn': '9781593279288',
        'publisher': 'No Starch Press',
        'year_published': 2019,
        'category': 'Technology',
        'subcategory': 'Programming',
        'description': 'A comprehensive introduction to Python for beginners, covering syntax, data structures, and real-world applications.',
        'total_physical_copies': 5,
        'available_physical_copies': 4,
        'has_digital': True,
    },
    {
        'title': 'Things Fall Apart',
        'author': 'Chinua Achebe',
        'isbn': '9780385474542',
        'publisher': 'Anchor',
        'year_published': 1994,
        'category': 'Literature',
        'subcategory': 'African Fiction',
        'description': 'A classic of African literature depicting the collision of Igbo culture with British colonial rule.',
        'total_physical_copies': 3,
        'available_physical_copies': 2,
        'has_digital': True,
    },
    {
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'isbn': '9780132350884',
        'publisher': 'Prentice Hall',
        'year_published': 2008,
        'category': 'Technology',
        'subcategory': 'Software Engineering',
        'description': 'A handbook of agile software craftsmanship — writing code that humans can read and maintain.',
        'total_physical_copies': 2,
        'available_physical_copies': 1,
        'has_digital': True,
    },
    {
        'title': 'The Republic',
        'author': 'Plato',
        'isbn': '9780140449143',
        'publisher': 'Penguin Classics',
        'year_published': 2007,
        'category': 'Philosophy',
        'subcategory': 'Classical',
        'description': 'A Socratic dialogue concerning justice, the just city-state, and the just man.',
        'total_physical_copies': 4,
        'available_physical_copies': 4,
        'has_digital': False,
    },
    {
        'title': 'A Brief History of Time',
        'author': 'Stephen Hawking',
        'isbn': '9780553380163',
        'publisher': 'Bantam',
        'year_published': 1998,
        'category': 'Science',
        'subcategory': 'Physics',
        'description': 'Exploring cosmology, black holes, and the nature of time for the general reader.',
        'total_physical_copies': 2,
        'available_physical_copies': 2,
        'has_digital': True,
    },
    {
        'title': 'The Beautiful Things That Heaven Bears',
        'author': 'Dinaw Mengestu',
        'isbn': '9781594482854',
        'publisher': 'Riverhead Books',
        'year_published': 2007,
        'category': 'Literature',
        'subcategory': 'African Fiction',
        'description': 'An Ethiopian immigrant\u2019s story of displacement and longing in Washington, D.C.',
        'total_physical_copies': 3,
        'available_physical_copies': 3,
        'has_digital': False,
    },
    {
        'title': 'Half of a Yellow Sun',
        'author': 'Chimamanda Ngozi Adichie',
        'isbn': '9781400095209',
        'publisher': 'Anchor',
        'year_published': 2006,
        'category': 'Literature',
        'subcategory': 'African Fiction',
        'description': 'A novel set during the Biafran War, weaving together the lives of three characters.',
        'total_physical_copies': 4,
        'available_physical_copies': 2,
        'has_digital': True,
    },
    {
        'title': 'We Wish to Inform You That Tomorrow We Will Be Killed with Our Families',
        'author': 'Philip Gourevitch',
        'isbn': '9780312243237',
        'publisher': 'Picador',
        'year_published': 1999,
        'category': 'History',
        'subcategory': 'African History',
        'description': 'A journalistic account of the Rwandan genocide and its aftermath.',
        'total_physical_copies': 2,
        'available_physical_copies': 2,
        'has_digital': False,
    },
    {
        'title': 'The Art of Computer Programming, Vol. 1',
        'author': 'Donald E. Knuth',
        'isbn': '9780201896831',
        'publisher': 'Addison-Wesley',
        'year_published': 1997,
        'category': 'Technology',
        'subcategory': 'Algorithms',
        'description': 'The seminal work on algorithms and analysis, covering fundamental mathematical concepts.',
        'total_physical_copies': 2,
        'available_physical_copies': 2,
        'has_digital': False,
    },
    {
        'title': 'Sapiens: A Brief History of Humankind',
        'author': 'Yuval Noah Harari',
        'isbn': '9780062316097',
        'publisher': 'Harper',
        'year_published': 2015,
        'category': 'History',
        'subcategory': 'World History',
        'description': 'A sweeping narrative of human history from the Stone Age to the modern era.',
        'total_physical_copies': 5,
        'available_physical_copies': 4,
        'has_digital': True,
    },
    {
        'title': 'Design Patterns',
        'author': 'Erich Gamma et al.',
        'isbn': '9780201633610',
        'publisher': 'Addison-Wesley',
        'year_published': 1994,
        'category': 'Technology',
        'subcategory': 'Software Engineering',
        'description': 'Elements of reusable object-oriented software — the classic Gang of Four catalog.',
        'total_physical_copies': 3,
        'available_physical_copies': 3,
        'has_digital': False,
    },
    {
        'title': 'The Wright Brothers',
        'author': 'David McCullough',
        'isbn': '9781476728759',
        'publisher': 'Simon & Schuster',
        'year_published': 2015,
        'category': 'Biography',
        'subcategory': 'Historical',
        'description': 'The story of Wilbur and Orville Wright and their pursuit of human flight.',
        'total_physical_copies': 2,
        'available_physical_copies': 2,
        'has_digital': False,
    },
    {
        'title': 'Homegoing',
        'author': 'Yaa Gyasi',
        'isbn': '9781101971060',
        'publisher': 'Vintage',
        'year_published': 2016,
        'category': 'Literature',
        'subcategory': 'African Fiction',
        'description': 'A novel tracing the parallel paths of two half-sisters and their descendants across 300 years of Ghanaian and American history.',
        'total_physical_copies': 4,
        'available_physical_copies': 4,
        'has_digital': True,
    },
    {
        'title': 'Ghana Must Go',
        'author': 'Taiye Selasi',
        'isbn': '9781594632733',
        'publisher': 'Penguin Press',
        'year_published': 2013,
        'category': 'Literature',
        'subcategory': 'African Fiction',
        'description': 'A novel of a fractured family reunited in Ghana after the patriarch\u2019s death.',
        'total_physical_copies': 3,
        'available_physical_copies': 3,
        'has_digital': False,
    },
    {
        'title': 'Americanah',
        'author': 'Chimamanda Ngozi Adichie',
        'isbn': '9780307455925',
        'publisher': 'Anchor',
        'year_published': 2013,
        'category': 'Literature',
        'subcategory': 'African Fiction',
        'description': 'A story of love, race, and identity spanning Nigeria, the United States, and the UK.',
        'total_physical_copies': 4,
        'available_physical_copies': 3,
        'has_digital': True,
    },
]


def _make_user(full_name, email, role, password, *,
               student_id=None, username=None, department=None,
               year_of_study=None, approval_status='approved'):
    u = User(
        full_name=full_name,
        email=email,
        role=role,
        username=username,
        student_id=student_id,
        department=department,
        year_of_study=year_of_study,
        is_active=True,
        approval_status=approval_status,
    )
    u.set_password(password)
    db.session.add(u)
    return u


def seed():
    app = create_app()
    with app.app_context():
        # Wipe and recreate all tables.
        db.drop_all()
        db.create_all()
        init_default_settings()

        # ---- Users (sample seed data) ----------------------------
        admin = _make_user(
            'Adwoa Boateng', 'admin@sankofa.edu', 'admin', 'admin12345',
            username='admin',
        )
        librarian = _make_user(
            'Kwabena Owusu', 'librarian@sankofa.edu', 'librarian', 'librarian123',
            username='librarian',
        )
        student1 = _make_user(
            'Kwame Mensah', 'kwame.mensah@st.knust.edu.gh', 'student', 'student123',
            student_id='STU2024001', username='kwame.mensah',
            department='Computer Science', year_of_study=2,
        )
        student2 = _make_user(
            'Ama Osei', 'ama.osei@st.knust.edu.gh', 'student', 'student123',
            student_id='STU2024002', username='ama.osei',
            department='English Literature', year_of_study=3,
        )
        student3 = _make_user(
            'Kofi Asante', 'kofi.asante@st.knust.edu.gh', 'student', 'student123',
            student_id='STU2024003', username='kofi.asante',
            department='Mathematics', year_of_study=1,
        )
        pending_student = _make_user(
            'Akosua Frimpong', 'akosua.frimpong@st.knust.edu.gh', 'student',
            'student123',
            student_id='STU2024004', username='akosua.frimpong',
            department='History & Political Studies', year_of_study=2,
            approval_status='pending',
        )

        db.session.flush()

        # ---- Library cards for all students ----------------------------
        for s in [student1, student2, student3, pending_student]:
            db.session.add(LibraryCard(
                user_id=s.user_id,
                card_number=generate_library_card_number(s.student_id),
            ))

        # ---- Books ------------------------------------------------------
        created_books = []
        for book_data in BOOKS_DATA:
            b = Book(**book_data, is_active=True)
            if b.isbn:
                print(f"Fetching cover for {b.title} (ISBN: {b.isbn})...")
                cover = fetch_cover_by_isbn(b.isbn)
                if cover:
                    b.cover_image = cover
            db.session.add(b)
            created_books.append(b)

        db.session.flush()

        # ---- Digital content for books that have has_digital=True ------

        # uploads/books/ so the in-browser reader has something to serve.
        uploads_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(uploads_dir, exist_ok=True)

        sample_content = (
            'SANKOFA LIBRARY SYSTEM — SAMPLE DIGITAL BOOK\n'
            '============================================\n\n'
            'This is a sample digital book for demonstration purposes.\n'
            'In production, upload PDF or HTML files for each book.\n\n'
            'Chapter 1: Introduction\n'
            '-----------------------\n'
            'Welcome to the Sankofa Library online reading portal.\n'
            'Your library card verification ensures secure access to '
            'digital resources.\n\n'
            'Chapter 2: Reading Online\n'
            '-------------------------\n'
            'After verifying your library card, you can read books directly '
            'in your browser.\nAll reading sessions are logged for audit '
            'purposes.\n'
        )
        for b in created_books:
            if b.has_digital:
                filename = f'book_{b.book_id}_{b.isbn}.txt'
                filepath = os.path.join(uploads_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(sample_content.replace(
                        'SANKOFA LIBRARY SYSTEM', b.title.upper()
                    ))
                b.digital_file_path = filepath

        db.session.flush()

        # ---- Checkouts (5: 1 overdue, 2 active, 2 returned) ------------
        today = date.today()
        day = timedelta(days=1)

        overdue_checkout = Checkout(
            user_id=student1.user_id,
            book_id=created_books[1].book_id,  # Things Fall Apart
            librarian_id=librarian.user_id,
            checkout_date=today - 20 * day,
            expected_return_date=today - 6 * day,
            status='overdue',
        )
        db.session.add(overdue_checkout)

        active1 = Checkout(
            user_id=student2.user_id,
            book_id=created_books[6].book_id,  # Half of a Yellow Sun
            librarian_id=librarian.user_id,
            checkout_date=today - 9 * day,
            expected_return_date=today + 5 * day,
            status='active',
        )
        db.session.add(active1)

        active2 = Checkout(
            user_id=student2.user_id,
            book_id=created_books[14].book_id,  # Americanah
            librarian_id=librarian.user_id,
            checkout_date=today - 12 * day,
            expected_return_date=today + 2 * day,
            status='active',
        )
        db.session.add(active2)

        history_checkout = Checkout(
            user_id=student3.user_id,
            book_id=created_books[2].book_id,  # Clean Code
            librarian_id=librarian.user_id,
            checkout_date=today - 30 * day,
            expected_return_date=today - 16 * day,
            actual_return_date=today - 18 * day,
            status='returned',
        )
        db.session.add(history_checkout)

        late_checkout = Checkout(
            user_id=student3.user_id,
            book_id=created_books[9].book_id,  # Sapiens
            librarian_id=librarian.user_id,
            checkout_date=today - 40 * day,
            expected_return_date=today - 26 * day,
            actual_return_date=today - 20 * day,
            status='returned',
        )
        db.session.add(late_checkout)

        db.session.flush()

        # ---- 1 fine (for the late Sapiens return — 6 days overdue) -----
        fine = Fine(
            checkout_id=late_checkout.checkout_id,
            user_id=student3.user_id,
            days_overdue=6,
            amount_per_day=1.00,
            total_amount=6.00,
            status='issued',
            processed_by=librarian.user_id,
        )
        db.session.add(fine)

        # ---- 1 reading session (Kwame read the Python book) ------------
        from datetime import datetime
        reading_session = ReadingSession(
            user_id=student1.user_id,
            book_id=created_books[0].book_id,  # Introduction to Python
            card_verified=True,
            session_start=datetime.utcnow() - 2 * day,
            session_end=datetime.utcnow() - 1 * day,
        )
        db.session.add(reading_session)

        # ---- Audit log entries -----------------------------------------
        db.session.add(AuditLog(
            actor_id=admin.user_id,
            action_type='SYSTEM_INIT',
            description='Library system initialised with seed data',
        ))
        db.session.add(AuditLog(
            actor_id=librarian.user_id,
            action_type='CHECKOUT',
            target_table='checkouts',
            target_id=overdue_checkout.checkout_id,
            description=(
                f'Checked out "{created_books[1].title}" to '
                f'{student1.full_name}'
            ),
        ))
        db.session.add(AuditLog(
            actor_id=librarian.user_id,
            action_type='CHECKOUT',
            target_table='checkouts',
            target_id=late_checkout.checkout_id,
            description=(
                f'Checked out "{created_books[9].title}" to '
                f'{student3.full_name}'
            ),
        ))
        db.session.add(AuditLog(
            actor_id=librarian.user_id,
            action_type='RETURN',
            target_table='checkouts',
            target_id=late_checkout.checkout_id,
            description=(
                f'Returned "{created_books[9].title}" — fine issued (GHS 6.00)'
            ),
        ))
        db.session.add(AuditLog(
            actor_id=librarian.user_id,
            action_type='RETURN',
            target_table='checkouts',
            target_id=history_checkout.checkout_id,
            description=(
                f'Returned "{created_books[2].title}" on time'
            ),
        ))
        db.session.add(AuditLog(
            action_type='REGISTER',
            target_table='users',
            target_id=pending_student.user_id,
            description=(
                f'New student registration: {pending_student.full_name} '
                f'({pending_student.student_id}) — awaiting approval'
            ),
        ))

        db.session.commit()

        # ---- Console summary -------------------------------------------
        print('=' * 60)
        print('Sankofa Library System — seed complete')
        print('=' * 60)
        print(f'Users:       6 (admin, librarian, 4 students — 1 pending)')
        print(f'Books:       {len(created_books)}')
        print(f'Checkouts:   5 (1 overdue, 2 active, 2 returned)')
        print(f'Fines:       1 (GHS 6.00 issued)')
        print(f'Sessions:    1 reading session')
        print(f'Settings:    8 system settings')
        print()
        print('--- Login Credentials ---')
        print('Admin:       admin@sankofa.edu / admin12345')
        print('Librarian:   librarian@sankofa.edu / librarian123')
        print('Students:    kwame.mensah@st.knust.edu.gh / student123')
        print('             ama.osei@st.knust.edu.gh / student123')
        print('             kofi.asante@st.knust.edu.gh / student123')
        print('(pending:    akosua.frimpong@st.knust.edu.gh / student123)')
        print()
        print('--- Library Cards ---')
        for s in [student1, student2, student3, pending_student]:
            print(f'  {s.full_name}: {s.library_card.card_number}')


if __name__ == '__main__':
    seed()
