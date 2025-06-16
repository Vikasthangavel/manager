from flask import Flask, render_template, request, redirect, url_for, flash, session
from db import get_manager_by_email_and_password, get_all_customers, add_customer, update_customer, delete_customer, add_pending_manager, update_customer_balance, add_payment, get_payment_history
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
import smtplib
import string
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'manager_secret_key')
bcrypt = Bcrypt(app)

# Email configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

def generate_password(length=8):
    """Generate a random password."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def send_email(to_email, mobile_number, password):
    """Send login credentials to the customer's email with an HTML template."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = 'Your Time2cable Account Credentials'

        # HTML email body with inline CSS
        html_body = f"""
        <html>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; margin: 20px auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <!-- Header -->
                <tr>
                    <td style="background-color: #008080; padding: 20px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px;">
                        <h1 style="color: #ffffff; font-size: 24px; margin: 0;">Welcome to Time2Due</h1>
                    </td>
                </tr>
                <!-- Body -->
                <tr>
                    <td style="padding: 30px; color: #1F2A44;">
                        <h2 style="font-size: 20px; color: #008080; margin-top: 0;">Account Created Successfully</h2>
                        <p style="font-size: 16px; line-height: 1.5; margin: 10px 0;">Dear Customer,</p>
                        <p style="font-size: 16px; line-height: 1.5; margin: 10px 0;">
                            Your Time2Due account has been created successfully. Below are your login credentials:
                        </p>
                        <table border="0" cellpadding="10" cellspacing="0" style="width: 100%; background-color: #E6F5F5; border-radius: 4px; margin: 20px 0;">
                            <tr>
                                <td style="font-size: 16px; font-weight: bold; color: #1F2A44;">Mobile Number:</td>
                                <td style="font-size: 16px; color: #1F2A44;">{mobile_number}</td>
                            </tr>
                            <tr>
                                <td style="font-size: 16px; font-weight: bold; color: #1F2A44;">Password:</td>
                                <td style="font-size: 16px; color: #1F2A44;">{password}</td>
                            </tr>
                        </table>
                        <p style="font-size: 16px; line-height: 1.5; margin: 10px 0; color: #EF4444;">
                            <strong>Important:</strong> Please keep this information secure and do not share it with anyone.
                        </p>
                        <p style="font-size: 16px; line-height: 1.5; margin: 10px 0;">
                            You can log in to your account using these credentials.
                        </p>
                    </td>
                </tr>
                <!-- Footer -->
                <tr>
                    <td style="background-color: #008080; padding: 15px; text-align: center; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;">
                        <p style="font-size: 14px; color: #ffffff; margin: 0;">Regards,<br>Time2Due Team</p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        # Attach the HTML body to the email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

# Middleware for manager authentication
def manager_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' not in session or session['role'] != 'manager':
            flash('Please log in as manager to access this page.', 'error')
            return redirect(url_for('manager_login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Manager signup
@app.route('/signup', methods=['GET', 'POST'])
def manager_signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        success, message = add_pending_manager(username, email, mobile_number, password)
        flash(message, 'success' if success else 'error')
        if success:
            return redirect(url_for('manager_login'))
    return render_template('manager_signup.html')

# Manager login
@app.route('/', methods=['GET', 'POST'])
def manager_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        manager = get_manager_by_email_and_password(email, password)
        if manager:
            session['logged_in'] = True
            session['user_id'] = manager['id']
            session['role'] = 'manager'
            flash('Manager login successful!', 'success')
            return redirect(url_for('manager_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('manager_login.html')

# Manager logout
@app.route('/logout')
def manager_logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('manager_login'))

# Manager dashboard
@app.route('/dashboard')
@manager_required
def manager_dashboard():
    manager_id = session['user_id']
    customers = get_all_customers(manager_id=manager_id)
    payments = get_payment_history(manager_id=manager_id)
    if not customers and customers != []:
        flash('Database connection failed!', 'error')
        return render_template('manager_dashboard.html', customers=[], payments=[])
    if not payments and payments != []:
        flash('Failed to fetch payment history.', 'error')
        payments = []
    return render_template('manager_dashboard.html', customers=customers, payments=payments)

# Add customer
@app.route('/add_customer', methods=['POST'])
@manager_required
def add_customer_route():
    box_number = request.form['box_number']
    mobile_number = request.form['mobile_number']
    name = request.form['name']
    email = request.form.get('email')
    # Generate a random password for the customer
    password = generate_password()
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    plan_amount = request.form['plan_amount']
    address = request.form['address']
    manager_id = session['user_id']
    
    # Add customer to the database with is_temp_password=True
    success, message = add_customer(box_number, mobile_number, name, email, hashed_password, plan_amount, address, manager_id, is_temp_password=True)
    
    if success and email:
        # Send email with credentials
        email_success, email_message = send_email(email, mobile_number, password)
        if not email_success:
            flash(f"Customer added, but {email_message}", 'warning')
        else:
            flash(f"{message} and credentials sent to customer's email.", 'success')
    elif success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('manager_dashboard'))

# Edit customer
@app.route('/edit_customer/<int:customer_id>', methods=['POST'])
@manager_required
def edit_customer(customer_id):
    box_number = request.form['box_number']
    mobile_number = request.form['mobile_number']
    name = request.form['name']
    email = request.form.get('email')
    password = request.form.get('password')
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8') if password else None
    is_temp_password = bool(password)  # Set is_temp_password to True if a new password is provided
    plan_amount = request.form['plan_amount']
    address = request.form['address']
    success, message = update_customer(customer_id, box_number, mobile_number, name, email, hashed_password, plan_amount, address, is_temp_password)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('manager_dashboard'))

# Delete customer
@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
@manager_required
def delete_customer_route(customer_id):
    success, message = delete_customer(customer_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('manager_dashboard'))

# Add bill for single customer
@app.route('/add_bill/<int:customer_id>', methods=['POST'])
@manager_required
def add_bill(customer_id):
    manager_id = session['user_id']
    customers = get_all_customers(manager_id=manager_id)
    if not customers and customers != []:
        flash('Database connection failed!', 'error')
        return redirect(url_for('manager_dashboard'))
    if not customers:
        flash('No customers found.', 'error')
        return redirect(url_for('manager_dashboard'))
    
    customer = next((c for c in customers if c['id'] == customer_id), None)
    if not customer:
        flash('Customer not found.', 'error')
        return redirect(url_for('manager_dashboard'))
    
    plan_amount = float(customer['plan_amount'])
    success, message = update_customer_balance(customer_id, plan_amount)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('manager_dashboard'))

# Add bills for all customers
@app.route('/add_all_bills', methods=['POST'])
@manager_required
def add_all_bills():
    manager_id = session['user_id']
    customers = get_all_customers(manager_id=manager_id)
    if not customers and customers != []:
        flash('Database connection failed!', 'error')
        return redirect(url_for('manager_dashboard'))
    
    if not customers:
        flash('No customers found.', 'error')
        return redirect(url_for('manager_dashboard'))
    
    success_count = 0
    for customer in customers:
        plan_amount = float(customer['plan_amount'])
        success, message = update_customer_balance(customer['id'], plan_amount)
        if success:
            success_count += 1
    
    flash(f'Bills added successfully for {success_count} customers.', 'success')
    return redirect(url_for('manager_dashboard'))

@app.route('/pay_offline/<int:customer_id>', methods=['POST'])
@manager_required
def pay_offline(customer_id):
    manager_id = session['user_id']
    customers = get_all_customers(manager_id)
    customer = next((c for c in customers if c['id'] == customer_id), None)
    if not customer:
        flash('Customer not found.', 'error')
        return redirect(url_for('manager_dashboard'))
    
    try:
        amount = float(request.form['amount'])
        if amount > float(customer['balance']):
            flash('Payment amount cannot exceed current balance.', 'error')
            return redirect(url_for('manager_dashboard'))
        
        # Add payment record
        ist_timestamp = datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
        success, message = add_payment(
            customer_id=customer_id,
            manager_id=customer['manager_id'],
            amount=amount,
            payment_mode='offline',  # Fixed: Changed to 'offline' to match route intent
            payment_status='completed',
            payment_reference=None,  # Fixed: order_id was undefined, set to None for offline payments
            payment_date=ist_timestamp,
            created_at=ist_timestamp
        )
        if not success:
            flash(message, 'error')
            return redirect(url_for('manager_dashboard'))
        
        # Subtract amount from balance
        success, message = update_customer_balance(customer_id, -amount)
        flash(message, 'success' if success else 'error')
        return redirect(url_for('manager_dashboard'))
    
    except ValueError:
        flash('Invalid payment amount.', 'error')
        return redirect(url_for('manager_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5002)
