from datetime import datetime, date

from flask_login import UserMixin

from app.extensions import db, bcrypt



class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('student', 'librarian', 'admin', name='user_role'), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    profile_photo = db.Column(db.String(255), nullable=True)

    library_card = db.relationship('LibraryCard', backref='user', uselist=False, cascade='all, delete-orphan')
    checkouts = db.relationship('Checkout', foreign_keys='Checkout.user_id', backref='student', lazy='dynamic')
    fines = db.relationship('Fine', foreign_keys='Fine.user_id', backref='student', lazy='dynamic')
    reading_sessions = db.relationship('ReadingSession', backref='user', lazy='dynamic')

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_librarian(self):
        return self.role == 'librarian'

    @property
    def is_admin(self):
        return self.role == 'admin'


class LibraryCard(db.Model):
    __tablename__ = 'library_cards'

    card_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    card_number = db.Column(db.String(50), unique=True, nullable=False)
    issued_date = db.Column(db.Date, default=date.today, nullable=False)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Book(db.Model):
    __tablename__ = 'books'

    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    publisher = db.Column(db.String(150), nullable=True)
    year_published = db.Column(db.Integer, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    total_physical_copies = db.Column(db.Integer, default=0, nullable=False)
    available_physical_copies = db.Column(db.Integer, default=0, nullable=False)
    has_digital = db.Column(db.Boolean, default=False, nullable=False)
    digital_file_path = db.Column(db.String(500), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    checkouts = db.relationship('Checkout', backref='book', lazy='dynamic')
    reading_sessions = db.relationship('ReadingSession', backref='book', lazy='dynamic')

    @property
    def copies_checked_out(self):
        return self.total_physical_copies - self.available_physical_copies


class Checkout(db.Model):
    __tablename__ = 'checkouts'

    checkout_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'), nullable=False)
    librarian_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    checkout_date = db.Column(db.Date, nullable=False)
    expected_return_date = db.Column(db.Date, nullable=False)
    actual_return_date = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.Enum('active', 'returned', 'overdue', name='checkout_status'),
        default='active',
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    librarian = db.relationship('User', foreign_keys=[librarian_id])
    fine = db.relationship('Fine', backref='checkout', uselist=False)

    @property
    def days_overdue(self):
        if self.status == 'returned' or self.actual_return_date:
            return 0
        today = date.today()
        if today <= self.expected_return_date:
            return 0
        return (today - self.expected_return_date).days


class Fine(db.Model):
    __tablename__ = 'fines'

    fine_id = db.Column(db.Integer, primary_key=True)
    checkout_id = db.Column(db.Integer, db.ForeignKey('checkouts.checkout_id'), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    days_overdue = db.Column(db.Integer, nullable=False)
    amount_per_day = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(
        db.Enum('pending', 'issued', 'waived', 'paid', name='fine_status'),
        default='issued',
        nullable=False,
    )
    waiver_reason = db.Column(db.Text, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    processor = db.relationship('User', foreign_keys=[processed_by])


class ReadingSession(db.Model):
    __tablename__ = 'reading_sessions'

    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'), nullable=False)
    card_verified = db.Column(db.Boolean, default=False, nullable=False)
    session_start = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    action_type = db.Column(db.String(100), nullable=False)
    target_table = db.Column(db.String(100), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship('User', foreign_keys=[actor_id])


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    setting_id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Report(db.Model):
    __tablename__ = 'reports'
    id           = db.Column(db.Integer, primary_key=True)
    report_type  = db.Column(db.String(50), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    student_name = db.Column(db.String(100))
    book_title   = db.Column(db.String(200))
    description  = db.Column(db.Text, nullable=False)
    severity     = db.Column(db.String(20), default='medium')
    filed_by     = db.Column(db.Integer, db.ForeignKey('users.user_id'))  # change 'users' to match yours
    date_filed   = db.Column(db.DateTime, default=datetime.utcnow)

    filer = db.relationship('User', foreign_keys=[filed_by])
