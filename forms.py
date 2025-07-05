from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange, Optional
import datetime

# Registration form
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Transaction form for adding income/expense
class TransactionForm(FlaskForm):
    type = SelectField('Type', choices=[('Income', 'Income'), ('Expense', 'Expense')], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message='Amount must be positive')])
    category = SelectField('Category', choices=[], validators=[DataRequired()])  # Choices will be set in the route
    description = TextAreaField('Description', validators=[Optional()])
    date = DateField('Date', default=datetime.date.today, validators=[DataRequired()])
    submit = SubmitField('Add Transaction')

# Budget form for setting monthly category budgets
class BudgetForm(FlaskForm):
    category = SelectField('Category', choices=[], validators=[DataRequired()])  # Choices will be set in the route
    amount = FloatField('Monthly Budget', validators=[DataRequired(), NumberRange(min=0.01, message='Budget must be positive')])
    month = SelectField('Month', choices=[], validators=[DataRequired()])  # Choices will be set in the route
    submit = SubmitField('Set Budget')

# Category form for adding custom categories
class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=50, message='Category name must be between 2 and 50 characters')])
    submit = SubmitField('Add Category') 