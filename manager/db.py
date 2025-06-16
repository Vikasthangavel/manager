import os
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import check_password_hash
from datetime import datetime

def connect():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'time2cable'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'root')
    )

def get_user_by_email_and_password(email, password):
    conn = connect()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        conn.close()

def get_manager_by_email_and_password(email, password):
    conn = connect()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        # Only use email in the SQL query, password is checked separately below
        cursor.execute("SELECT * FROM managers WHERE email = %s", (email,))
        manager = cursor.fetchone()
        if manager:
            if check_password_hash(manager['password'], password):
                return manager
        return None
    finally:
        cursor.close()
        conn.close()


def get_customer_by_mobile_and_password(mobile_number, password):
    conn = connect()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE mobile_number = %s", (mobile_number,))
        customer = cursor.fetchone()
        from flask_bcrypt import check_password_hash
        if customer and check_password_hash(customer['password'], password):
            return customer
        return None
    finally:
        cursor.close()
        conn.close()

def get_all_customers(customer_id=None, manager_id=None):
    conn = connect()
    if not conn:
        print("Database connection failed in get_all_customers")
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        if customer_id:
            print(f"Fetching customer with customer_id: {customer_id}")
            cursor.execute("""
                SELECT id, box_number, mobile_number, name, email, plan_amount, address, created_at, manager_id, balance, is_temp_password
                FROM customers WHERE id = %s
            """, (customer_id,))
        elif manager_id:
            print(f"Fetching customers for manager_id: {manager_id}")
            cursor.execute("""
                SELECT id, box_number, mobile_number, name, email, plan_amount, address, created_at, manager_id, balance, is_temp_password
                FROM customers WHERE manager_id = %s
            """, (manager_id,))
        else:
            print("Fetching all customers (no filter)")
            cursor.execute("""
                SELECT id, box_number, mobile_number, name, email, plan_amount, address, created_at, manager_id, balance, is_temp_password
                FROM customers
            """)
        customers = cursor.fetchall()
        print(f"Retrieved {len(customers)} customers: {customers}")
        return customers if customers else []
    except Error as e:
        print(f"Error fetching customers: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_payment_history(manager_id):
    conn = connect()
    if not conn:
        print("Database connection failed in get_payment_history")
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.customer_id, p.amount, p.payment_mode, p.payment_status, p.payment_date
            FROM payments p
            JOIN customers c ON p.customer_id = c.id
            WHERE c.manager_id = %s
            ORDER BY p.payment_date DESC
        """, (manager_id,))
        payments = cursor.fetchall()
        for payment in payments:
            if isinstance(payment['payment_date'], str):
                payment['payment_date'] = datetime.strptime(payment['payment_date'], '%Y-%m-%d %H:%M:%S')
        print(f"Retrieved {len(payments)} payments for manager_id {manager_id}: {payments}")
        return payments if payments else []
    except Error as e:
        print(f"Error fetching payment history: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def add_customer(box_number, mobile_number, name, email, password, plan_amount, address, manager_id, is_temp_password=False):
    conn = connect()
    if not conn:
        print("Database connection failed in add_customer")
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (box_number, mobile_number, name, email, password, plan_amount, address, manager_id, is_temp_password)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (box_number, mobile_number, name, email, password, plan_amount, address, manager_id, is_temp_password))
        conn.commit()
        print(f"Customer added: mobile={mobile_number}, manager_id={manager_id}, is_temp_password={is_temp_password}")
        return True, "Customer added successfully"
    except Error as e:
        conn.rollback()
        print(f"Error adding customer: {str(e)}")
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def update_customer(customer_id, box_number, mobile_number, name, email, password, plan_amount, address, is_temp_password):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        if password:
            cursor.execute("""
                UPDATE customers
                SET box_number = %s, mobile_number = %s, name = %s, email = %s, password = %s, plan_amount = %s, address = %s, is_temp_password = %s
                WHERE id = %s
            """, (box_number, mobile_number, name, email, password, plan_amount, address, is_temp_password, customer_id))
        else:
            cursor.execute("""
                UPDATE customers
                SET box_number = %s, mobile_number = %s, name = %s, email = %s, plan_amount = %s, address = %s, is_temp_password = %s
                WHERE id = %s
            """, (box_number, mobile_number, name, email, plan_amount, address, is_temp_password, customer_id))
        conn.commit()
        return True, "Customer updated successfully"
    except Error as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def delete_customer(customer_id):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        conn.commit()
        return True, "Customer deleted successfully"
    except Error as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def add_pending_manager(username, email, mobile_number, password):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pending_users (username, email, mobile_number, password)
            VALUES (%s, %s, %s, %s)
        """, (username, email, mobile_number, password))
        conn.commit()
        return True, "Manager signup request submitted successfully"
    except Error as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def get_pending_managers():
    conn = connect()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, email, mobile_number FROM pending_users")
        pending_managers = cursor.fetchall()
        return pending_managers
    finally:
        cursor.close()
        conn.close()

def approve_manager(pending_user_id):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_users WHERE id = %s", (pending_user_id,))
        pending_manager = cursor.fetchone()
        if not pending_manager:
            return False, "Pending manager not found"
        cursor.execute("""
            INSERT INTO managers (username, email, mobile_number, password)
            VALUES (%s, %s, %s, %s)
        """, (pending_manager[1], pending_manager[2], pending_manager[3], pending_manager[4]))
        cursor.execute("DELETE FROM pending_users WHERE id = %s", (pending_user_id,))
        conn.commit()
        return True, "Manager approved successfully"
    except Error as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def reject_manager(pending_user_id):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_users WHERE id = %s", (pending_user_id,))
        conn.commit()
        return True, "Manager signup request rejected"
    except Error as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def update_customer_balance(customer_id, amount):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor(dictionary=True)
        # Get current balance
        cursor.execute("SELECT balance FROM customers WHERE id = %s", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            return False, "Customer not found"
        
        # Calculate new balance
        current_balance = float(customer['balance'])
        amount = float(amount)
        new_balance = current_balance + amount
        
        if new_balance < 0:
            return False, "Balance cannot be negative"
        
        # Update balance
        cursor.execute(
            "UPDATE customers SET balance = %s WHERE id = %s",
            (new_balance, customer_id)
        )
        conn.commit()
        return True, "Balance updated successfully"
    except Error as e:
        conn.rollback()
        return False, f"Error updating balance: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def add_payment(customer_id, manager_id, amount, payment_mode, payment_status, payment_reference):
    conn = connect()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payments (customer_id, manager_id, amount, payment_mode, payment_status, payment_reference)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (customer_id, manager_id, amount, payment_mode, payment_status, payment_reference))
        conn.commit()
        return True, "Payment recorded successfully"
    except Error as e:
        conn.rollback()
        return False, f"Error recording payment: {str(e)}"
    finally:
        cursor.close()
        conn.close()