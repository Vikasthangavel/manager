
# Pay offline
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
