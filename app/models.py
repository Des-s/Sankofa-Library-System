"""SQLAlchemy models — faithful port of the Next.js Prisma schema.

Every model maps to the corresponding Prisma model in prisma/schema.prisma.
Composite indexes match the @@index directives. Enums are mirrored as
SQLAlchemy db.Enum columns with the same names and values as the Prisma
enums (UserRole, ApprovalStatus, CheckoutStatus, FineStatus, ReportType).

The Prisma schema uses String IDs (cuids); we use Integer PKs for parity
with Flask-SQLAlchemy conventions. All other field names and semantics
match exactly.
"""
from datetime import date, datetime

from flask_login import UserMixin
from sqlalchemy import Numeric

from app.extensions import bcrypt, db


# ---------------------------------------------------------------------------
# User — mirrors Prisma `User`
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    username = db.Column(db.String(50), unique=True, nullable=True, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum('student', 'librarian', 'admin', name='user_role'),
        nullable=False, default='student',
    )
    department = db.Column(db.String(100), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    approval_status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name='approval_status'),
        default='approved', nullable=False,
    )
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    theme_preference = db.Column(db.String(10), default='light', nullable=False)
    language_preference = db.Column(db.String(10), default='en', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )

    __table_args__ = (
        db.Index('ix_users_role_active', 'role', 'is_active'),
        db.Index('ix_users_approval_status', 'approval_status'),
    )

    # ---- Relationships (mirror Prisma relation fields) ---------------
    library_card = db.relationship(
        'LibraryCard', backref='user', uselist=False,
        cascade='all, delete-orphan',
    )
    checkouts = db.relationship(
        'Checkout', foreign_keys='Checkout.user_id',
        backref='student', lazy='dynamic',
    )
    librarian_checkouts = db.relationship(
        'Checkout', foreign_keys='Checkout.librarian_id',
        backref='librarian', lazy='dynamic',
    )
    fines = db.relationship(
        'Fine', foreign_keys='Fine.user_id',
        backref='student', lazy='dynamic',
    )
    reading_sessions = db.relationship(
        'ReadingSession', backref='user', lazy='dynamic',
    )
    audit_logs = db.relationship(
        'AuditLog', foreign_keys='AuditLog.actor_id',
        backref='actor', lazy='dynamic',
    )
    reports_filed = db.relationship(
        'Report', foreign_keys='Report.filed_by',
        backref='filer', lazy='dynamic',
    )
    reports_about = db.relationship(
        'Report', foreign_keys='Report.student_id',
        backref='subject', lazy='dynamic',
    )
    processed_fines = db.relationship(
        'Fine', foreign_keys='Fine.processed_by',
        backref='processor', lazy='dynamic',
    )

    # ---- Flask-Login contract -----------------------------------------
    def get_id(self):
        return str(self.user_id)

    # ---- Password helpers (mirror src/lib/auth.ts hashPassword) ------
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    # ---- Role helpers (mirror Next.js role checks) -------------------
    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_librarian(self):
        return self.role == 'librarian'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def initials(self):
        parts = (self.full_name or '').split()
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()


# ---------------------------------------------------------------------------
# LibraryCard — mirrors Prisma `LibraryCard`
# ---------------------------------------------------------------------------
class LibraryCard(db.Model):
    __tablename__ = 'library_cards'

    card_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.user_id'),
        nullable=False, unique=True,
    )
    card_number = db.Column(db.String(50), unique=True, nullable=False)
    issued_date = db.Column(db.Date, default=date.today, nullable=False)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )


# ---------------------------------------------------------------------------
# Book — mirrors Prisma `Book`
# ---------------------------------------------------------------------------
class Book(db.Model):
    __tablename__ = 'books'

    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    publisher = db.Column(db.String(150), nullable=True)
    year_published = db.Column(db.Integer, nullable=True)
    category = db.Column(db.String(100), nullable=True, index=True)
    subcategory = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    total_physical_copies = db.Column(db.Integer, default=0, nullable=False)
    available_physical_copies = db.Column(db.Integer, default=0, nullable=False)
    has_digital = db.Column(db.Boolean, default=False, nullable=False)
    digital_file_path = db.Column(db.String(500), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )

    __table_args__ = (
        db.Index('ix_books_category_active', 'category', 'is_active'),
        db.Index('ix_books_active', 'is_active'),
    )

    checkouts = db.relationship('Checkout', backref='book', lazy='dynamic')
    reading_sessions = db.relationship('ReadingSession', backref='book', lazy='dynamic')

    @property
    def copies_checked_out(self):
        return max(0, self.total_physical_copies - self.available_physical_copies)


# ---------------------------------------------------------------------------
# Checkout — mirrors Prisma `Checkout`
# ---------------------------------------------------------------------------
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
        default='active', nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )

    __table_args__ = (
        db.Index('ix_checkouts_status_expected', 'status', 'expected_return_date'),
        db.Index('ix_checkouts_user_status', 'user_id', 'status'),
        db.Index('ix_checkouts_book', 'book_id'),
    )

    fine = db.relationship('Fine', backref='checkout', uselist=False)

    @property
    def days_overdue(self):
        if self.status == 'returned' or self.actual_return_date:
            return 0
        today = date.today()
        if today <= self.expected_return_date:
            return 0
        return (today - self.expected_return_date).days

    @property
    def days_until_due(self):
        today = date.today()
        if today > self.expected_return_date:
            return -((today - self.expected_return_date).days)
        return (self.expected_return_date - today).days


# ---------------------------------------------------------------------------
# Fine — mirrors Prisma `Fine`
# ---------------------------------------------------------------------------
class Fine(db.Model):
    __tablename__ = 'fines'

    fine_id = db.Column(db.Integer, primary_key=True)
    checkout_id = db.Column(
        db.Integer, db.ForeignKey('checkouts.checkout_id'),
        nullable=False, unique=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    days_overdue = db.Column(db.Integer, nullable=False, default=0)
    amount_per_day = db.Column(Numeric(10, 2), nullable=False)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    status = db.Column(
        db.Enum('pending', 'issued', 'waived', 'paid', name='fine_status'),
        default='issued', nullable=False,
    )
    waiver_reason = db.Column(db.Text, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )

    __table_args__ = (
        db.Index('ix_fines_user_status', 'user_id', 'status'),
        db.Index('ix_fines_status', 'status'),
    )


# ---------------------------------------------------------------------------
# ReadingSession — mirrors Prisma `ReadingSession`
# ---------------------------------------------------------------------------
class ReadingSession(db.Model):
    __tablename__ = 'reading_sessions'

    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'), nullable=False)
    card_verified = db.Column(db.Boolean, default=False, nullable=False)
    session_start = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )

    __table_args__ = (
        db.Index('ix_reading_sessions_user_end', 'user_id', 'session_end'),
    )


# ---------------------------------------------------------------------------
# AuditLog — mirrors Prisma `AuditLog`
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    action_type = db.Column(db.String(100), nullable=False)
    target_table = db.Column(db.String(100), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('ix_audit_action_created', 'action_type', 'created_at'),
        db.Index('ix_audit_created', 'created_at'),
    )

    # actor relationship defined on User as `audit_logs`; backref here:
    # (defined via User.audit_logs backref — no need to redefine)


# ---------------------------------------------------------------------------
# SystemSetting — mirrors Prisma `SystemSetting`
# ---------------------------------------------------------------------------
class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    setting_id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow, nullable=False,
    )


# ---------------------------------------------------------------------------
# Report — mirrors Prisma `Report`
# ---------------------------------------------------------------------------
class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    student_name = db.Column(db.String(100), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    book_title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='medium', nullable=False)
    filed_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    date_filed = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('ix_reports_type', 'report_type'),
        db.Index('ix_reports_filed', 'date_filed'),
    )
