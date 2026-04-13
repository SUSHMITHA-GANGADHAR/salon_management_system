import os
import time
import hmac
import hashlib
import requests
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
import bcrypt

# Load environment variables
load_dotenv()

# ==============================================================================
# DEFINITIVE DATABASE CONNECTION (FORCE PRODUCTION CONFIG)
# ==============================================================================
_supabase_client = None

def get_db():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    
    # 1. Try Environment Variables (Render Dashboard)
    url = os.environ.get('SUPABASE_URL') or os.getenv('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY') or os.getenv('SUPABASE_KEY')
    
    # 2. EMERGENCY FALLBACK: Hardcoded Production Credentials
    # (Provided by the developer to ensure the system works 100% on Render)
    if not url or not key:
        print("DEBUG: Using Hardcoded Production Credentials...")
        url = "https://jyjxsltnbzlotlmeqwpn.supabase.co"
        # Using Service Role Key for full database access
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5anhzbHRuYnpsb3RsbWVxd3BuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzE0Nzc3OSwiZXhwIjoyMDg4NzIzNzc5fQ.rQJmmx-_GUOW_papli2cItCHHCS-gfEBSZAaI-6BJYc"
        
    try:
        _supabase_client = create_client(url, key)
        print("DEBUG: Supabase Connection Initialized Successfully.")
        return _supabase_client
    except Exception as e:
        print(f"FAILED TO CONNECT TO SUPABASE: {e}")
        return None

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.getenv('SECRET_KEY') or "default_secret_key_123"
CORS(app)

# Razorpay Configuration (Hardcoded Fallback for reliability)
RAZOR_KEY_ID = os.environ.get('RAZOR_KEY_ID') or os.getenv('RAZOR_KEY_ID') or "rzp_test_SPAZS8RUI3LyK3"
RAZOR_KEY_SECRET = os.environ.get('RAZOR_KEY_SECRET') or os.getenv('RAZOR_KEY_SECRET') or "ji7GTXEPsyqBZeC7qWKlfYqK"

def verify_razorpay_signature(params):
    try:
        msg = f"{params['razorpay_order_id']}|{params['razorpay_payment_id']}"
        generated = hmac.new(
            RAZOR_KEY_SECRET.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()
        return generated == params['razorpay_signature']
    except:
        return False

# ===== DB RETRY HELPER =====
def get_salon_settings():
    try:
        db = get_db()
        if not db: return {'name': 'Salon Pro', 'address': '123 Luxury Lane'}
        res = db.table('salon_settings').select('*').eq('id', 1).single().execute()
        return res.data
    except:
        return {'name': 'Salon Pro', 'address': '123 Luxury Lane'}

def db_retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    print(f"Database attempt {i+1} failed: {e}. Retrying...")
                    time.sleep(delay)
            raise last_error
        return wrapper
    return decorator

# Authentication helper
def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if not is_logged_in(): return None
    db = get_db()
    if not db: return None
    try:
        user_id = session.get('user_id')
        response = db.table('users').select('*').eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

# ===== ROUTES =====

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        gender = data.get('gender', 'male')
        role = data.get('role', 'customer')
        
        if not all([name, email, password]):
            return jsonify({'success': False, 'message': 'Registration forms must be complete.'}), 400
        
        try:
            db = get_db()
            if not db: return jsonify({'success': False, 'message': 'Database connection error.'}), 500
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.table('users').insert({
                'name': name,
                'email': email,
                'password': hashed,
                'role': role,
                'gender': gender
            }).execute()
            return jsonify({'success': True, 'redirect': '/login'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        try:
            db = get_db()
            if not db: return jsonify({'success': False, 'message': 'Database connection error.'}), 500
            response = db.table('users').select('*').eq('email', email).execute()
            if not response.data:
                return jsonify({'success': False, 'message': 'Account not found'}), 401
            
            user = response.data[0]
            if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                return jsonify({'success': False, 'message': 'Incorrect password'}), 401
            
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            session['gender'] = user['gender']
            
            redirect_url = '/dashboard'
            if user['role'] == 'admin': redirect_url = '/admin-dashboard'
            elif user['role'] == 'staff': redirect_url = '/staff-dashboard'
            
            return jsonify({'success': True, 'redirect': redirect_url})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/booking/cancel', methods=['POST'])
def cancel_booking():
    if not is_logged_in(): return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data = request.json
    bid = data.get('booking_id')
    reason = data.get('reason', 'No reason provided')
    try:
        db = get_db()
        if not db: return jsonify({'success': False, 'message': 'Database connection error.'}), 500
        db.table('appointments').update({
            'status': 'cancelled',
            'cancellation_reason': reason
        }).eq('id', bid).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user: return redirect('/login')
    role = session.get('role')
    if role != 'customer':
        return redirect('/admin-dashboard' if role == 'admin' else '/staff-dashboard')
    
    try:
        db = get_db()
        if not db: return "Database connection error.", 500
        res = db.table('appointments').select('*, services(*)').eq('user_id', user['id']).order('date').execute()
        bookings = res.data
        today_dt = date.today()
        for b in bookings:
            b_date = datetime.strptime(b['date'], '%Y-%m-%d').date()
            b['can_cancel'] = b_date > today_dt and b['status'] != 'cancelled'
    except Exception as e:
        print(f"Dashboard Error: {e}")
        bookings = []
        
    return render_template('dashboard.html', user=user, bookings=bookings)

@app.route('/booking')
def booking_page():
    if not is_logged_in(): return redirect('/login')
    gender = session.get('gender') or 'male'
    try:
        db = get_db()
        if not db: return "Database connection error.", 500
        res = db.table('services').select('*').eq('gender', gender).execute()
        services = res.data
    except:
        services = []
    return render_template('booking.html', services=services)

@app.route('/staff-dashboard')
def staff_dashboard():
    user = get_current_user()
    if not user or session.get('role') != 'staff': return redirect('/login')
    try:
        db = get_db()
        if not db: return "Database connection error.", 500
        res = db.table('appointments').select('*, customer:user_id(name), services(name, price), specialist:staff_id(name)').neq('status', 'cancelled').order('date').execute()
        bookings = res.data
    except Exception as e:
        print(f"Staff Dashboard Error: {e}")
        bookings = []
    return render_template('staff-dashboard.html', user=user, bookings=bookings)

@app.route('/admin-dashboard')
def admin_dashboard():
    user = get_current_user()
    if not user or session.get('role') != 'admin': return redirect('/login')
    try:
        db = get_db()
        if not db: return "Database connection error.", 500
        results = db.table('appointments').select('*, customer:user_id(name, email), services(*)').order('date').execute()
        all_bookings = results.data
        customers = db.table('users').select('id', count='exact').eq('role', 'customer').execute()
        staff = db.table('users').select('*').eq('role', 'staff').execute()
        
        revenue = 0
        for b in all_bookings:
            if b['status'] != 'cancelled':
                revenue += 50
                if b.get('balance_paid'):
                    price = b['services']['price'] if b.get('services') else 50
                    revenue += (price - 50)
                    
        return render_template('admin-dashboard.html', 
                             user=user, 
                             bookings=all_bookings, 
                             users_count=len(customers.data) if customers.data else 0,
                             revenue=revenue,
                             staff=staff.data if staff.data else [])
    except Exception as e:
        print(f"Admin Dashboard Error: {e}")
        return render_template('admin-dashboard.html', user=user, bookings=[], users_count=0, revenue=0, staff=[])

@app.route('/api/booking/collect-balance', methods=['POST'])
def collect_balance():
    if not is_logged_in() or session.get('role') not in ['admin', 'staff']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data = request.json
    booking_id = data.get('id')
    try:
        db = get_db()
        if not db: return jsonify({'success': False}), 500
        db.table('appointments').update({
            'balance_paid': True,
            'status': 'finished'
        }).eq('id', booking_id).execute()
        return jsonify({'success': True, 'message': 'Balance collected!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/payment/create-order', methods=['POST'])
def create_order():
    if not is_logged_in(): return jsonify({'success': False}), 403
    amount = 50 * 100 # In paise
    try:
        res = requests.post(
            'https://api.razorpay.com/v1/orders',
            auth=(RAZOR_KEY_ID, RAZOR_KEY_SECRET),
            json={'amount': amount, 'currency': 'INR', 'payment_capture': 1}
        )
        order = res.json()
        return jsonify({'success': True, 'order_id': order['id'], 'amount': amount})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    data = request.json
    try:
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }
        if not verify_razorpay_signature(params_dict):
            raise Exception("Invalid Signature")

        db = get_db()
        if not db: return jsonify({'success': False}), 500
        db.table('appointments').insert({
            'user_id': session['user_id'],
            'service_id': data.get('service_id'),
            'date': data.get('date'),
            'time': data.get('time'),
            'status': 'pending',
            'payment_id': data.get('razorpay_payment_id'),
            'payment_amount': 50,
            'balance_paid': False
        }).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/update-status', methods=['POST'])
def update_status():
    if not is_logged_in() or session.get('role') not in ['admin', 'staff']:
        return jsonify({'success': False}), 403
    data = request.json
    booking_id = data.get('id')
    new_status = data.get('status')
    try:
        db = get_db()
        if not db: return jsonify({'success': False}), 500
        db.table('appointments').update({'status': new_status}).eq('id', booking_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/reschedule', methods=['POST'])
def reschedule_booking():
    if not is_logged_in() or session.get('role') not in ['admin', 'staff']:
        return jsonify({'success': False}), 403
    data = request.json
    booking_id = data.get('id')
    new_date = data.get('date')
    new_time = data.get('time')
    try:
        db = get_db()
        if not db: return jsonify({'success': False}), 500
        db.table('appointments').update({
            'date': new_date,
            'time': new_time,
            'status': 'pending'
        }).eq('id', booking_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-staff', methods=['POST'])
def add_staff():
    if not is_logged_in() or session.get('role') != 'admin':
        return jsonify({'success': False}), 403
    data = request.get_json()
    try:
        db = get_db()
        if not db: return jsonify({'success': False}), 500
        hashed = bcrypt.hashpw(data.get('password').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.table('users').insert({
            'name': data.get('name'),
            'email': data.get('email'),
            'password': hashed,
            'role': 'staff',
            'gender': data.get('gender', 'male')
        }).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-service', methods=['POST'])
def add_service():
    if not is_logged_in() or session.get('role') != 'admin':
        return jsonify({'success': False}), 403
    data = request.get_json()
    try:
        db = get_db()
        if not db: return jsonify({'success': False}), 500
        db.table('services').insert({
            'name': data.get('name'),
            'price': float(data.get('price')),
            'gender': data.get('gender'),
            'description': data.get('description', '')
        }).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/available-slots')
def available_slots():
    date = request.args.get('date')
    service_id = request.args.get('service_id')
    try:
        db = get_db()
        if not db: return jsonify([])
        booked = db.table('appointments').select('time').eq('service_id', service_id).eq('date', date).eq('status', 'confirmed').execute()
        booked_times = [b['time'] for b in booked.data]
        all_slots = [f"{h:02d}:00" for h in range(9, 18)]
        available = [s for s in all_slots if s not in booked_times]
        return jsonify(available)
    except:
        return jsonify([])

@app.route('/api/staff/available')
def staff_available():
    date = request.args.get('date')
    time = request.args.get('time')
    try:
        db = get_db()
        if not db: return jsonify([])
        all_staff = db.table('users').select('id, name').eq('role', 'staff').execute()
        try:
            busy = db.table('appointments').select('staff_id').eq('date', date).eq('time', time).eq('status', 'confirmed').execute()
            busy_ids = [b['staff_id'] for b in busy.data]
        except:
            busy_ids = []
        available = [s for s in all_staff.data if s['id'] not in busy_ids]
        return jsonify(available)
    except:
        return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
