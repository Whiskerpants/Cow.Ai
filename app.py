from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# Flask-WTF Signup Form
class SignupForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email is required."),
        Email(message="Invalid email address. Please enter a valid email.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    operation_name = StringField('Operation Name', validators=[
        DataRequired(message="Operation Name is required.")
    ])
    submit = SubmitField('Sign Up')
# Define LoginForm using Flask-WTF
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
import os

# App Initialization
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cows.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a strong secret key
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    operation_name = db.Column(db.String(100), nullable=False)

# Cow Model
class Cow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cow_id = db.Column(db.String(20), unique=True, nullable=False)
    last_estrus_date = db.Column(db.Date, nullable=False)
    cycle_length_days = db.Column(db.Integer, default=21)
    correct_prediction = db.Column(db.Boolean, default=False)
    successful_pregnancy = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "cow_id": self.cow_id,
            "last_estrus_date": self.last_estrus_date.strftime('%Y-%m-%d'),
            "cycle_length_days": self.cycle_length_days,
            "next_estrus_date": (self.last_estrus_date + timedelta(days=self.cycle_length_days)).strftime('%Y-%m-%d'),
            "correct_prediction": self.correct_prediction,
            "successful_pregnancy": self.successful_pregnancy,
        }

# Initialize the database
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    print("Accessing home route")
    print("Current Working Directory:", os.getcwd())
    if current_user.is_authenticated:
        print("User is authenticated, redirecting to service selection")
        return redirect(url_for('service_selection'))  # Redirect logged-in users to service selection
    print("User is not authenticated, rendering home page")
    return render_template('index.html')  # Show landing page for unauthenticated users

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if request.method == 'POST':
        print("Signup form submitted!")  # Debugging

    if form.validate_on_submit():
        print("Form validation passed!")  # Debugging
        email = form.email.data
        password = form.password.data
        operation_name = form.operation_name.data

        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already registered. Please log in.", "danger")
            print("User already exists!")  # Debugging
            return redirect(url_for('login'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_password, operation_name=operation_name)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        print("User created successfully!")  # Debugging
        return redirect(url_for('login'))
    else:
        print("Form validation failed!")  # Debugging
        flash("Form validation failed. Please check your inputs.", "danger")

    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('service_selection'))
        flash("Invalid email or password.", "danger")
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/service_selection')
@login_required
def service_selection():
    return render_template('service_selection.html')

@app.route('/hdp')
@login_required
def hdp():
    cows = Cow.query.all()  # Fetch all cows from database
    return render_template('hdp.html', cows=cows)
    try:
        return render_template('hdp.html')
    except Exception as e:
        return f"Error loading template: {str(e)}"

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100))
    date = db.Column(db.Date)
    amount = db.Column(db.Float)
    notes = db.Column(db.Text)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    date = db.Column(db.Date)
    amount = db.Column(db.Float)
    vendor = db.Column(db.String(100))
    notes = db.Column(db.Text)
@app.route('/F.R.O')
@login_required
def bookkeeping_dashboard():
    incomes = Income.query.all()
    expenses = Expense.query.all()
    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    profit = total_income - total_expense
    return render_template('F.R.O_dashboard.html',
                           incomes=incomes,
                           expenses=expenses,
                           total_income=total_income,
                           total_expense=total_expense,
                           profit=profit)
@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if request.method == 'POST':
        new_income = Income(
            source=request.form['source'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            amount=float(request.form['amount']),
            notes=request.form['notes']
        )
        db.session.add(new_income)
        db.session.commit()
        return redirect('/bookkeeping')
    return render_template('income.html')

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        new_expense = Expense(
            category=request.form['category'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            amount=float(request.form['amount']),
            vendor=request.form['vendor'],
            notes=request.form['notes']
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect('/bookkeeping')
    return render_template('expense.html')
@app.route('/get-cow-data/<cow_id>', methods=['GET'])
@login_required
def get_cow_data(cow_id):
    print(f"Fetching data for Cow ID: {cow_id}")  # Debugging
    cow = Cow.query.filter_by(cow_id=cow_id).first()
    if cow:
        return jsonify(cow.to_dict())
    print("Cow not found!")  # Debugging
    return jsonify({"error": "Cow not found"}), 404


@app.route('/update-cow-data', methods=['POST'])
@login_required
def update_cow_data():
    data = request.json
    cow = Cow.query.filter_by(cow_id=data["cow_id"]).first()

    if not cow:
        return jsonify({"error": "Cow not found"}), 404

    try:
        cow.last_estrus_date = datetime.strptime(data["last_estrus_date"], '%Y-%m-%d')
        cow.cycle_length_days = int(data["cycle_length_days"])

        if "correct_prediction" in data:
            cow.correct_prediction = bool(data["correct_prediction"])
        if "successful_pregnancy" in data:
            cow.successful_pregnancy = bool(data["successful_pregnancy"])

        db.session.commit()  # Ensure changes are committed
        return jsonify({"message": f"Cow {cow.cow_id} updated successfully"})
    except Exception as e:
        print(f"Error updating cow: {e}")
        return jsonify({"error": "Failed to update cow"}), 500

@app.route('/get-all-cows', methods=['GET'])
@login_required
def get_all_cows():
    cows = Cow.query.all()
    cow_list = [cow.to_dict() for cow in cows]
    return jsonify(cow_list)

@app.route('/add-cow', methods=['POST'])
@login_required
def add_cow():
    data = request.json

    existing_cow = Cow.query.filter_by(cow_id=data["cow_id"]).first()
    if existing_cow:
        return jsonify({"error": "Cow ID already exists"}), 400

    try:
        new_cow = Cow(
            cow_id=data["cow_id"],
            last_estrus_date=datetime.strptime(data["last_estrus_date"], '%Y-%m-%d'),
            cycle_length_days=int(data["cycle_length_days"]),
            correct_prediction=bool(data.get("correct_prediction", False)),
            successful_pregnancy=bool(data.get("successful_pregnancy", False))
        )
        db.session.add(new_cow)
        db.session.commit()
        return jsonify({"message": f"Cow {new_cow.cow_id} added successfully"})
    except Exception as e:
        print(f"Error adding cow: {e}")
        return jsonify({"error": "Failed to add cow"}), 500

@app.route('/delete-cow/<cow_id>', methods=['DELETE'])
@login_required
def delete_cow(cow_id):
    cow = Cow.query.filter_by(cow_id=cow_id).first()
    if cow:
        db.session.delete(cow)
        db.session.commit()
        return jsonify({"message": f"Cow {cow_id} deleted successfully"})
    return jsonify({"error": "Cow not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)

from flask_migrate import Migrate
migrate = Migrate(app, db)
