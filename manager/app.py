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

def send_email(to_email, subject, template_type, **kwargs):
    """Send an email with a specified template type (credential or bill_notification)."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject

        if template_type == 'credential':
            mobile_number = kwargs.get('mobile_number')
            password = kwargs.get('password')
            # HTML email body for account credentials with website link
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd;">
                    <h2 style="color: #007bff;">Welcome to Time2Due</h2>
                    <h3>Account Created Successfully</h3>
                    <p>Dear Customer,</p>
                    <p>Your Time2Due account has been created successfully. Below are your login credentials:</p>
                    <ul>
                        <li><strong>Mobile Number:</strong> {mobile_number}</li>
                        <li><strong>Password:</strong> {password}</li>
                    </ul>
                    <p><strong>Important:</strong> Please keep this information secure and do not share it with anyone.</p>
                    <p>You can log in to your account using these credentials by visiting our website:</p>
                    <p style="text-align: center;">
                        <a href="https://www.time2due.com" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px;">Click Me</a>
                    </p>
                    <p>Regards,<br>Time2Due Team</p>
                </div>
            </body>
            </html>
            """
        elif template_type == 'bill_notification':
            name = kwargs.get('name')
            amount = kwargs.get('amount')
            # HTML email body for bill notification with enhanced styling
            html_body = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>New Bill Generated</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Arial', 'Helvetica', sans-serif; color: #333333; background-color: #f4f7fa;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f7fa; padding: 20px;">
                    <tr>
                        <td align="center">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
                                <!-- Header -->
                                <tr>
                                    <td style="background-color: #007bff; padding: 20px; text-align: center;">
                                        <!-- Logo Placeholder (Uncomment and replace src if logo is available) -->
                                        <!-- <img src="https://www.time2due.com/logo.png" alt="Time2Due Logo" style="max-width: 150px;"> -->
                                        <h2 style="color: #ffffff; font-size: 24px; margin: 10px 0;">New Bill Generated</h2>
                                    </td>
                                </tr>
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 30px;">
                                        <h3 style="font-size: 20px; color: #007bff; margin: 0 0 15px;">Bill Notification</h3>
                                        <p style="font-size: 16px; line-height: 24px; margin: 0 0 10px;">Dear {name},</p>
                                        <p style="font-size: 16px; line-height: 24px; margin: 0 0 20px;">
                                            A new bill Cable <strong style="color: #333333;">₹{amount:.2f}</strong> has been generated for your account.
                                        </p>
                                        <p style="font-size: 16px; line-height: 24px; margin: 0 0 20px;">
                                            Please visit our website to pay your bill and keep your account active:
                                        </p>
                                        <!-- Call-to-Action Button -->
                                        <p style="text-align: center; margin: 30px 0;">
                                            <a href="https://www.time2due.com" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold; border: 2px solid #0056b3;">Pay Now</a>
                                        </p>
                                        <p style="font-size: 14px; line-height: 22px; color: #666666; margin: 0 0 10px;">
                                            If you have any questions, please contact our support team at <a href="mailto:support@time2due.com" style="color: #007bff; text-decoration: none;">support@time2due.com</a>.
                                        </p>
                                    </td>
                                </tr>
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666666; border-top: 1px solid #e0e0e0;">
                                        <p style="margin: 0;">Regards,<br>The Time2Due Team</p>
                                        <p style="margin: 10px 0 0;">
                                            <a href="https://www.time2due.com" style="color: #007bff; text-decoration: none;">www.time2due.com</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
        else:
            return False, "Invalid template type"

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
        email_success, email_message = send_email(
            to_email=email,
            subject='Your Time2Due Account Credentials',
            template_type='credential',
            mobile_number=mobile_number,
            password=password
        )
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
    email_success_count = 0
    email_failures = []
    
    for customer in customers:
        plan_amount = float(customer['plan_amount'])
        success, message = update_customer_balance(customer['id'], plan_amount)
        if success:
            success_count += 1
            # Send bill notification email if customer has an email
            if customer.get('email'):
                email_success, email_message = send_email(
                    to_email=customer['email'],
                    subject='New Bill Generated for Your Time2Due Account',
                    template_type='bill_notification',
                    name=customer['name'],
                    amount=plan_amount
                )
                if email_success:
                    email_success_count += 1
                else:
                    email_failures.append(f"{customer['name']} ({customer['email']}): {email_message}")
    
    flash(f'Bills added successfully for {success_count} customers.', 'success')
    if email_success_count > 0:
        flash(f'Bill notifications sent to {email_success_count} customers.', 'success')
    if email_failures:
        flash(f"Failed to send emails to {len(email_failures)} customers: {'; '.join(email_failures)}", 'warning')
    
    return redirect(url_for('manager_dashboard'))

# Pay offline
@app.route('/pay_offline/<int:customer_id>', methods=['POST'])
@manager_required
def pay_offline(customer_id):
    manager_id = session['user_id']
    customers = get_all_customers(manager_id=manager_id)
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
        success, message = add_payment(customer_id, manager_id, amount, 'offline', 'completed', None)
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