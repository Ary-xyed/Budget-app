from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Transaction, Budget, Category
from forms import RegistrationForm, LoginForm, TransactionForm, BudgetForm, CategoryForm
import os
import datetime
import calendar
import csv
import io

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route (redirect to dashboard or login)
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists. Please choose another.', 'danger')
            return render_template('register.html', form=form)
        # Create new user
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Default categories (can be expanded later)
DEFAULT_CATEGORIES = ['Food', 'Rent', 'Utilities', 'Transportation', 'Entertainment', 'Misc']

def get_current_month():
    # Returns current month as 'YYYY-MM'
    return datetime.date.today().strftime('%Y-%m')

def get_user_categories(user_id):
    # Get all categories for a user (default + custom)
    custom_categories = [c.name for c in Category.query.filter_by(user_id=user_id).all()]
    return sorted(set(DEFAULT_CATEGORIES + custom_categories))

@app.route('/manage_categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    form = CategoryForm()
    if form.validate_on_submit():
        # Check if category already exists for this user
        existing = Category.query.filter_by(user_id=current_user.id, name=form.name.data).first()
        if existing:
            flash('Category already exists!', 'danger')
        else:
            category = Category(user_id=current_user.id, name=form.name.data)
            db.session.add(category)
            db.session.commit()
            flash('Category added!', 'success')
        return redirect(url_for('manage_categories'))
    
    # Get user's categories
    custom_categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return render_template('manage_categories.html', form=form, categories=custom_categories)

@app.route('/delete_category/<int:category_id>')
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
    if category:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted!', 'success')
    else:
        flash('Category not found!', 'danger')
    return redirect(url_for('manage_categories'))

@app.route('/set_budget', methods=['GET', 'POST'])
@login_required
def set_budget():
    form = BudgetForm()
    # Set category choices (default + user's custom categories)
    all_categories = get_user_categories(current_user.id)
    form.category.choices = [(cat, cat) for cat in all_categories]
    # Set month choices (current and previous 5 months)
    months = [(datetime.date.today().replace(day=1) - datetime.timedelta(days=30*i)).strftime('%Y-%m') for i in range(6)]
    months = sorted(set(months), reverse=True)
    form.month.choices = [(m, m) for m in months]

    if form.validate_on_submit():
        # Check if budget already exists for this user/category/month
        budget = Budget.query.filter_by(user_id=current_user.id, category=form.category.data, month=form.month.data).first()
        if budget:
            budget.amount = form.amount.data  # Update existing
        else:
            budget = Budget(user_id=current_user.id, category=form.category.data, amount=form.amount.data, month=form.month.data)
            db.session.add(budget)
        db.session.commit()
        flash('Budget set!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('set_budget.html', form=form)

# Update dashboard to show budget vs. actual spending
@app.route('/dashboard')
@login_required
def dashboard():
    # Get current user's transactions for the current month
    current_month = get_current_month()
    transactions = Transaction.query.filter_by(user_id=current_user.id).filter(Transaction.date.like(f'{current_month}-%')).order_by(Transaction.date.desc()).all()
    total_income = sum(t.amount for t in transactions if t.type == 'Income')
    total_expenses = sum(t.amount for t in transactions if t.type == 'Expense')
    # Get budgets for current month
    budgets = Budget.query.filter_by(user_id=current_user.id, month=current_month).all()
    # Calculate spent per category
    spent_per_category = {}
    for t in transactions:
        if t.type == 'Expense':
            spent_per_category[t.category] = spent_per_category.get(t.category, 0) + t.amount
    # Prepare category_budgets for dashboard
    category_budgets = []
    for b in budgets:
        spent = spent_per_category.get(b.category, 0)
        category_budgets.append({
            'name': b.category,
            'budget': b.amount,
            'spent': spent
        })
    # Add categories with spending but no budget
    for cat, spent in spent_per_category.items():
        if not any(b['name'] == cat for b in category_budgets):
            category_budgets.append({'name': cat, 'budget': 0, 'spent': spent})
    
    # Generate pie chart data (spending by category)
    pie_labels = list(spent_per_category.keys())
    pie_data = list(spent_per_category.values())
    
    # Generate bar chart data (monthly spending for last 6 months)
    bar_labels = []
    bar_data = []
    for i in range(6):
        month = (datetime.date.today().replace(day=1) - datetime.timedelta(days=30*i)).strftime('%Y-%m')
        month_transactions = Transaction.query.filter_by(user_id=current_user.id).filter(Transaction.date.like(f'{month}-%')).all()
        month_expenses = sum(t.amount for t in month_transactions if t.type == 'Expense')
        bar_labels.append(month)
        bar_data.append(month_expenses)
    
    # Reverse to show oldest to newest
    bar_labels.reverse()
    bar_data.reverse()
    
    pagination = None
    return render_template(
        'dashboard.html',
        total_income=total_income,
        total_expenses=total_expenses,
        transactions=transactions,
        category_budgets=category_budgets,
        pie_labels=pie_labels,
        pie_data=pie_data,
        bar_labels=bar_labels,
        bar_data=bar_data,
        pagination=pagination
    )

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    # Set category choices (default + user's custom categories)
    all_categories = get_user_categories(current_user.id)
    form.category.choices = [(cat, cat) for cat in all_categories]

    if form.validate_on_submit():
        txn = Transaction(
            user_id=current_user.id,
            type=form.type.data,
            amount=form.amount.data,
            category=form.category.data,
            description=form.description.data,
            date=form.date.data
        )
        db.session.add(txn)
        db.session.commit()
        flash('Transaction added!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_transaction.html', form=form)

@app.route('/export_csv')
@login_required
def export_csv():
    # Get all user's transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    
    # Create CSV data in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Type', 'Amount', 'Category', 'Description'])
    
    # Write transaction data
    for txn in transactions:
        writer.writerow([
            txn.date.strftime('%Y-%m-%d'),
            txn.type,
            f"${txn.amount:.2f}",
            txn.category,
            txn.description or ''
        ])
    
    # Prepare file for download
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'budget_transactions_{current_user.username}_{datetime.date.today()}.csv'
    )

@app.route('/delete_transaction/<int:txn_id>')
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.filter_by(id=txn_id, user_id=current_user.id).first()
    if txn:
        db.session.delete(txn)
        db.session.commit()
        flash('Transaction deleted!', 'success')
    else:
        flash('Transaction not found or not authorized.', 'danger')
    return redirect(url_for('dashboard'))

# --- Database initialization and sample data seeding ---
# Use a flag to ensure seeding only happens once
seeded = False

@app.before_request
def create_tables_and_seed():
    global seeded
    if not seeded:
        db.create_all()
        # Seed sample users if not present
        if not User.query.filter_by(username='alice').first():
            user1 = User(username='alice')
            user1.set_password('password123')
            db.session.add(user1)
        if not User.query.filter_by(username='bob').first():
            user2 = User(username='bob')
            user2.set_password('password456')
            db.session.add(user2)
        db.session.commit()
        
        # Seed sample transactions for better chart visualization
        user1 = User.query.filter_by(username='alice').first()
        if user1 and not Transaction.query.filter_by(user_id=user1.id).first():
            # Add sample transactions for Alice
            sample_transactions = [
                Transaction(user_id=user1.id, type='Expense', amount=50.0, category='Food', description='Grocery shopping', date=datetime.date.today()),
                Transaction(user_id=user1.id, type='Expense', amount=1200.0, category='Rent', description='Monthly rent', date=datetime.date.today()),
                Transaction(user_id=user1.id, type='Expense', amount=80.0, category='Utilities', description='Electricity bill', date=datetime.date.today()),
                Transaction(user_id=user1.id, type='Income', amount=3000.0, category='Salary', description='Monthly salary', date=datetime.date.today()),
            ]
            for txn in sample_transactions:
                db.session.add(txn)
            db.session.commit()
        
        seeded = True

if __name__ == '__main__':
    app.run(debug=True) 