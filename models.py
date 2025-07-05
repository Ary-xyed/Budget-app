from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# Initialize SQLAlchemy (the actual app will initialize this in app.py)
db = SQLAlchemy()

# User model for authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        # Hash the password for secure storage
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Check the password against the stored hash
        return check_password_hash(self.password_hash, password)

# Transaction model for income and expenses
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to User
    type = db.Column(db.String(10), nullable=False)  # 'Income' or 'Expense'
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))  # Optional
    date = db.Column(db.Date, nullable=False)

    # Relationship to User (optional, for easy access)
    user = db.relationship('User', backref='transactions')

# Budget model for monthly category budgets
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to User
    category = db.Column(db.String(50), nullable=False)  # Category name
    amount = db.Column(db.Float, nullable=False)  # Monthly budget amount
    month = db.Column(db.String(7), nullable=False)  # Format: 'YYYY-MM' (e.g., '2024-01')

    # Relationship to User (optional, for easy access)
    user = db.relationship('User', backref='budgets')

    # Ensure one budget per category per month per user
    __table_args__ = (db.UniqueConstraint('user_id', 'category', 'month', name='unique_budget'),)

# Category model for user's custom categories
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to User
    name = db.Column(db.String(50), nullable=False)  # Category name
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)  # When it was created

    # Relationship to User (optional, for easy access)
    user = db.relationship('User', backref='custom_categories')

    # Ensure unique category names per user
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_category'),)

# More models (Transaction, Category, Budget) will be added here later. 