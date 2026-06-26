from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, DecimalField, FileField, HiddenField, IntegerField,
    PasswordField, SelectField, StringField, SubmitField, TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

from app.models import Book, User


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    student_id = StringField('Student ID', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    department = StringField('Department', validators=[DataRequired(), Length(max=100)])
    year_of_study = IntegerField('Year of Study', validators=[DataRequired(), NumberRange(min=1, max=6)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_student_id(self, field):
        if User.query.filter_by(student_id=field.data).first():
            raise ValidationError('This student ID is already registered.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('This email is already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    department = StringField('Department', validators=[DataRequired(), Length(max=100)])
    year_of_study = IntegerField('Year of Study', validators=[DataRequired(), NumberRange(min=1, max=6)])
    submit = SubmitField('Update Profile')


class CardVerificationForm(FlaskForm):
    card_number = StringField('Library Card Number', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Verify & Read')


class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    author = StringField('Author', validators=[DataRequired(), Length(max=255)])
    isbn = StringField('ISBN', validators=[DataRequired(), Length(max=20)])
    publisher = StringField('Publisher', validators=[Optional(), Length(max=150)])
    year_published = IntegerField('Year Published', validators=[Optional(), NumberRange(min=1000, max=2100)])
    category = StringField('Category', validators=[Optional(), Length(max=100)])
    total_physical_copies = IntegerField('Physical Copies', validators=[DataRequired(), NumberRange(min=0)])
    digital_file = FileField('Digital File (PDF/TXT/HTML)')
    is_active = BooleanField('Active in Catalog', default=True)
    submit = SubmitField('Save Book')


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
    password = PasswordField('Password', validators=[Optional(), Length(min=8)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save User')


class SystemSettingsForm(FlaskForm):
    fine_rate_per_day = DecimalField('Fine Rate (GHS/day)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    loan_period_days = IntegerField('Loan Period (days)', validators=[DataRequired(), NumberRange(min=1, max=90)])
    library_card_format = StringField('Card Format', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Save Settings')


class CatalogSearchForm(FlaskForm):
    q = StringField('Search', validators=[Optional()])
    category = SelectField('Category', validators=[Optional()])
    availability = SelectField('Availability', choices=[
        ('', 'All'),
        ('physical', 'Physical Available'),
        ('digital', 'Digital Available'),
    ], validators=[Optional()])
    submit = SubmitField('Search')
