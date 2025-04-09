
import os
import time
import random
import hashlib
import requests
from flask import Flask, request, render_template, redirect, jsonify, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Configuration - Replace with your actual credentials
GTRPAY_MERCHANT_ID = os.environ.get('GTRPAY_MERCHANT_ID')
GTRPAY_PASSAGE_ID = os.environ.get('GTRPAY_PASSAGE_ID')
GTRPAY_SECRET_KEY = os.environ.get('GTRPAY_SECRET_KEY')
GTRPAY_API_URL = 'https://wg.gtrpay001.com/collect/create'

# Generate a unique order number
def generate_order_number():
    timestamp = int(time.time() * 1000)
    random_num = random.randint(1000, 9999)
    return f"ORDER{timestamp}{random_num}"

# Generate signature for GTRPay
def generate_signature(params):
    # Sort keys alphabetically
    sorted_params = {k: params[k] for k in sorted(params.keys()) if k != 'sign' and params[k]}
    
    # Create string to sign
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params.items()])
    sign_str += f"&key={GTRPAY_SECRET_KEY}"
    
    # Create MD5 hash
    return hashlib.md5(sign_str.encode()).hexdigest()

# Create a payment request to GTRPay
def create_payment_request(amount, callback_url, remark=None):
    try:
        order_no = generate_order_number()
        
        params = {
            'mchId': GTRPAY_MERCHANT_ID,
            'passageId': GTRPAY_PASSAGE_ID,
            'orderAmount': amount,
            'orderNo': order_no,
            'notifyUrl': f"{callback_url}/gtrpay/callback",
            'callBackUrl': f"{callback_url}/deposit/success",
        }
        
        # Add optional parameters if provided
        if remark:
            params['remark'] = remark
        
        # Generate signature
        params['sign'] = generate_signature(params)
        
        # Make API request to GTRPay
        response = requests.post(GTRPAY_API_URL, json=params)
        data = response.json()
        
        if data['code'] == 200:
            return {
                'success': True,
                'pay_url': data['data']['payUrl'],
                'order_no': order_no
            }
        else:
            return {
                'success': False,
                'message': data.get('msg', 'Payment request failed')
            }
    except Exception as e:
        print(f"Error creating payment request: {e}")
        return {
            'success': False,
            'message': 'An error occurred while processing your request'
        }

@app.route('/')
def index():
    return redirect(url_for('deposit'))

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        amount = request.form.get('amount')
        site_url = request.form.get('site_url', '')
        remark = request.form.get('remark')
        
        # Validate inputs
        if not amount:
            flash('Amount is required', 'error')
            return render_template('deposit.html')
        
        try:
            # Convert amount to float to validate
            float_amount = float(amount)
            if float_amount <= 0:
                flash('Please enter a valid amount', 'error')
                return render_template('deposit.html')
        except ValueError:
            flash('Please enter a valid amount', 'error')
            return render_template('deposit.html')
        
        # If no site URL is provided, use the request's host URL
        if not site_url:
            site_url = request.host_url.rstrip('/')
            if request.headers.get('X-Forwarded-Proto') == 'https':
                site_url = site_url.replace('http:', 'https:')
        else:
            # Format site URL if needed
            if not site_url.startswith('http'):
                site_url = f"https://{site_url}"
            
            # Remove trailing slash if present
            if site_url.endswith('/'):
                site_url = site_url[:-1]
        
        # Create payment request
        result = create_payment_request(amount, site_url, remark)
        
        if result['success']:
            # Store order info in session for reference
            session['last_order_no'] = result['order_no']
            # Redirect to payment URL
            return redirect(result['pay_url'])
        else:
            flash(result['message'], 'error')
            return render_template('deposit.html')
    
    return render_template('deposit.html')

@app.route('/deposit/success')
def deposit_success():
    order_no = session.get('last_order_no', 'Unknown')
    return render_template('success.html', order_no=order_no)

@app.route('/gtrpay/callback', methods=['POST'])
def gtrpay_callback():
    try:
        data = request.json
        
        # Log the callback data for debugging
        print(f"Received callback from GTRPay: {data}")
        
      
        # Process the payment notification
        # Here you would update your database with the payment status
        order_no = data.get('orderNo')
        order_status = data.get('orderStatus')
        
        print(f"Processing payment for order {order_no} with status {order_status}")
        
        # Return success response
        return jsonify({'code': 200, 'msg': 'success'})
    except Exception as e:
        print(f"Error processing callback: {e}")
        return jsonify({'code': 400, 'msg': 'Error processing callback'})

@app.route('/ping')
def ping():
    """Simple endpoint to check if the service is running"""
    return jsonify({
        'status': 'success',
        'message': 'Service is running',
        'timestamp': time.time()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)