import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    BooleanField, DecimalField, HiddenField, IntegerField,
    PasswordField, SelectField, StringField, SubmitField, TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

from app.models import Book, User

STUDENT_EMAIL_DOMAIN = 'st.knust.edu.gh'


def validate_password_strength(form, field):
    if field.data and not (re.search(r'[A-Za-z]', field.data) and re.search(r'\d', field.data)):
        raise ValidationError('Password must contain at least one letter and one number.')


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    student_id = StringField('Student ID', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    department = StringField('Department', validators=[DataRequired(), Length(max=100)])
    year_of_study = IntegerField('Year of Study', validators=[DataRequired(), NumberRange(min=1, max=6)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8), validate_password_strength])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, field):
        username = field.data.strip().lower()
        if not re.match(r'^[a-zA-Z0-9_.]+$', username):
            raise ValidationError('Username may only contain letters, numbers, dots and underscores.')
        if User.query.filter(User.username.ilike(username)).first():
            raise ValidationError('This username is already taken.')

    def validate_student_id(self, field):
        student_id = field.data.strip().upper()
        if User.query.filter_by(student_id=student_id).first():
            raise ValidationError('This student ID is already registered.')

    def validate_email(self, field):
        email = field.data.strip().lower()
        if not email.endswith('@' + STUDENT_EMAIL_DOMAIN):
            raise ValidationError(f'You must register with your student email address (@{STUDENT_EMAIL_DOMAIN}).')
        if User.query.filter_by(email=email).first():
            raise ValidationError('This email is already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class CardVerificationForm(FlaskForm):
    card_number = StringField('Library Card Number', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Verify & Read')


class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    author = StringField('Author', validators=[DataRequired(), Length(max=255)])
    isbn = StringField('ISBN', validators=[DataRequired(), Length(max=20)])
    publisher = StringField('Publisher', validators=[Optional(), Length(max=150)])
    year_published = IntegerField('Year Published', validators=[Optional(), NumberRange(min=1000, max=2100)])
    category = StringField('Category (e.g. Science)', validators=[Optional(), Length(max=100)])
    subcategory = StringField('Subcategory (e.g. Biology)', validators=[Optional(), Length(max=100)])
    has_physical = SelectField('Physical Copies Available?', choices=[('yes', 'Yes'), ('no', 'No — digital only')], default='yes')
    total_physical_copies = IntegerField('Number of Physical Copies', validators=[Optional(), NumberRange(min=0)])
    digital_file = FileField('Digital File (PDF/TXT/HTML)')
    cover_image = FileField('Cover Image (leave blank to auto-fetch by ISBN)', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only')])
    is_active = BooleanField('Active in Catalog', default=True)
    submit = SubmitField('Save Book')

    def validate_total_physical_copies(self, field):
        if self.has_physical.data == 'yes' and not field.data:
            raise ValidationError('Enter the number of physical copies, or set "Physical Copies Available?" to No.')


class CheckoutForm(FlaskForm):
    student_search = StringField('Student ID or Name', validators=[DataRequired()])
    book_id = SelectField('Book', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Check Out Book')


class ReturnForm(FlaskForm):
    checkout_id = SelectField('Active Checkout', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Record Return')


class FineActionForm(FlaskForm):
    fine_id = HiddenField(validators=[DataRequired()])
    action = SelectField('Action', choices=[
        ('paid', 'Mark as Paid'),
        ('waived', 'Waive Fine'),
    ], validators=[DataRequired()])
    waiver_reason = TextAreaField('Reason (required for waiver)', validators=[Optional()])
    submit = SubmitField('Submit')


class UserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('librarian', 'Librarian'),
        ('admin', 'Administrator'),
    ], validators=[DataRequired()])
    student_id = StringField('Student ID', validators=[Optional(), Length(max=50)])
    department = StringField('Department', validators=[Optional(), Length(max=100)])
    year_of_study = IntegerField('Year of Study', validators=[Optional(), NumberRange(min=1, max=6)])
    password = PasswordField('Password', validators=[Optional(), Length(min=8), validate_password_strength])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save User')


class SystemSettingsForm(FlaskForm):
    fine_rate_per_day = DecimalField('Fine Rate (GHS/day)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    loan_period_days = IntegerField('Loan Period (days)', validators=[DataRequired(), NumberRange(min=1, max=90)])
    library_card_format = StringField('Card Format', validators=[DataRequired(), Length(max=100)])
    max_active_checkouts = IntegerField('Max Active Checkouts per Student', validators=[DataRequired(), NumberRange(min=1, max=50)])
    submit = SubmitField('Save Settings')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8), validate_password_strength])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')


class NotificationSettingsForm(FlaskForm):
    email_notifications = BooleanField('Email me notifications')
    submit = SubmitField('Save Preferences')


class ThemeForm(FlaskForm):
    dark_mode = BooleanField('Dark Mode')
    submit = SubmitField('Save Appearance')


class LanguageForm(FlaskForm):
    language_preference = SelectField('Language', choices=[('en', 'English'), ('fr', 'Français')], validators=[DataRequired()])
    submit = SubmitField('Save Language')


class ProfilePhotoForm(FlaskForm):
    profile_photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only')])
    submit = SubmitField('Upload Photo')


class SupportRequestForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Describe the problem', validators=[DataRequired()])
    submit = SubmitField('Submit')


class StudentEditForm(FlaskForm):
    department = StringField('Department', validators=[DataRequired(), Length(max=100)])
    year_of_study = IntegerField('Year of Study', validators=[DataRequired(), NumberRange(min=1, max=6)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Changes')


class CatalogSearchForm(FlaskForm):
    q = StringField('Search', validators=[Optional()])
    category = SelectField('Category', validators=[Optional()])
    availability = SelectField('Availability', choices=[
        ('', 'All'),
        ('physical', 'Physical Available'),
        ('digital', 'Digital Available'),
    ], validators=[Optional()])
    submit = SubmitField('Search')
