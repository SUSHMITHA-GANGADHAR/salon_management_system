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

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
CORS(app)

# Razorpay Configuration
RAZOR_KEY_ID = os.getenv('RAZOR_KEY_ID')
RAZOR_KEY_SECRET = os.getenv('RAZOR_KEY_SECRET')

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

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

print(f"DEBUG: SUPABASE_URL present: {'Yes' if SUPABASE_URL else 'No'}")
print(f"DEBUG: SUPABASE_KEY present: {'Yes' if SUPABASE_KEY else 'No'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("CRITICAL: SUPABASE_URL or SUPABASE_KEY not found in environment.")
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("DEBUG: Supabase Connection Initialized.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Supabase client: {e}")
        supabase = None

# ===== DB RETRY HELPER =====
def get_salon_settings():
    try:
        res = supabase.table('salon_settings').select('*').eq('id', 1).single().execute()
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

# ===== AUTH HELPER FUNCTIONS =====

def hash_password(password):
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if not is_logged_in() or not supabase: return None
    try:
        user_id = session.get('user_id')
        response = supabase.table('users').select('*').eq('id', user_id).execute()
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
            hashed = hash_password(password)
            supabase.table('users').insert({
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
            response = supabase.table('users').select('*').eq('email', email).execute()
            if not response.data:
                return jsonify({'success': False, 'message': 'Account not found'}), 401
            
            user = response.data[0]
            if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                return jsonify({'success': False, 'message': 'Incorrect password'}), 401
            
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['gender'] = user.get('gender') or 'male'
            
            print(f"USER LOGGED IN: ID={user['id']}, ROLE={user['role']}, GENDER={session['gender']}")
            
            target = '/dashboard'
            if user['role'] == 'admin': target = '/admin-dashboard'
            elif user['role'] == 'staff': target = '/staff-dashboard'
            
            return jsonify({'success': True, 'redirect': target})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    return render_template('login.html')

@app.route('/api/payment/create-order', methods=['POST'])
def create_order():
    if not is_logged_in(): return jsonify({'success': False}), 401
    # Fixed deposit amount: ₹50
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

@app.route('/api/booking/cancel', methods=['POST'])
def cancel_booking():
    if not is_logged_in(): return jsonify({'success': False}), 401
    data = request.get_json()
    bid = data.get('booking_id')
    reason = data.get('reason', 'No reason provided')
    try:
        supabase.table('appointments').update({
            'status': 'cancelled',
            'cancellation_reason': reason
        }).eq('id', bid).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    if not is_logged_in(): return redirect('/login')
    user = get_current_user()
    role = session.get('role', 'customer')
    if role != 'customer':
        return redirect('/admin-dashboard' if role == 'admin' else '/staff-dashboard')
    
    try:
        res = supabase.table('appointments').select('*, services(*)').eq('user_id', user['id']).order('date').execute()
        bookings = res.data
        today_dt = date.today()
        for b in bookings:
            b_date = datetime.strptime(b['date'], '%Y-%m-%d').date()
            diff = (b_date - today_dt).days
            b['days_left'] = diff if diff >= 0 else -1
    except:
        bookings = []
        
    return render_template('dashboard.html', user=user, bookings=bookings, RAZOR_KEY_ID=RAZOR_KEY_ID)

@app.route('/booking')
def booking():
    if not is_logged_in(): return redirect('/login')
    gender = session.get('gender') or 'male'
    print(f"FETCHING SERVICES FOR GENDER: {gender}")
    try:
        res = supabase.table('services').select('*').eq('gender', gender).execute()
        services = res.data
    except:
        services = []
    
    today = date.today().strftime('%Y-%m-%d')
    return render_template('booking.html', services=services, RAZOR_KEY_ID=RAZOR_KEY_ID, today=today)

@app.route('/staff-dashboard')
def staff_dashboard():
    if not is_logged_in() or session.get('role') != 'staff': return redirect('/login')
    user = get_current_user()
    try:
        # Fetch all bookings that are not cancelled or finished to show on active duty
        res = supabase.table('appointments').select('*, customer:user_id(name), services(name, price), specialist:staff_id(name)').neq('status', 'cancelled').order('date').execute()
        bookings = res.data
    except Exception as e:
        print(f"Staff Dashboard Error: {e}")
        bookings = []
    return render_template('staff-dashboard.html', user=user, bookings=bookings)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not is_logged_in() or session.get('role') != 'admin': return redirect('/login')
    user = get_current_user()
    try:
        # Fetch all bookings for analytics with explicit customer mapping
        results = supabase.table('appointments').select('*, customer:user_id(name, email), services(*)').order('date').execute()
        all_bookings = results.data
        
        customers = supabase.table('users').select('id', count='exact').eq('role', 'customer').execute()
        staff = supabase.table('users').select('*').eq('role', 'staff').execute()
        
        # Calculate revenue: 
        # 1. Start with initial deposits (₹50) from all paid bookings
        # 2. Add full price for 'finished' bookings where balance is settled
        total_revenue = 0
        for b in all_bookings:
            if b.get('is_paid'):
                if b.get('status') == 'finished' and b.get('services'):
                    total_revenue += b['services']['price']
                else:
                    total_revenue += 50 # Valid deposit even if not finished
        
        return render_template('admin-dashboard.html', 
                             user=user, 
                             bookings=all_bookings, 
                             users_count=customers.count or 0, 
                             revenue=total_revenue, 
                             staff=staff.data or [])
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
        supabase.table('appointments').update({
            'balance_paid': True,
            'status': 'finished'
        }).eq('id', booking_id).execute()
        return jsonify({'success': True, 'message': 'Balance collected! Service marked as complete.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/create-balance-order', methods=['POST'])
def create_balance_order():
    if not is_logged_in(): return jsonify({'success': False, 'message': 'Auth required'}), 401
    
    data = request.json
    booking_id = data.get('id')
    
    try:
        booking = supabase.table('appointments').select('*, services(*)').eq('id', booking_id).single().execute().data
        if not booking: return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Calculate remaining balance: Total - 50 deposit
        total_price = booking['services']['price']
        balance_amount = (total_price - 50) * 100 # Convert to paise
        
        if balance_amount <= 0:
            return jsonify({'success': False, 'message': 'No balance due.'})

        res = requests.post(
            'https://api.razorpay.com/v1/orders',
            auth=(RAZOR_KEY_ID, RAZOR_KEY_SECRET),
            json={'amount': int(balance_amount), 'currency': 'INR', 'payment_capture': 1}
        )
        order = res.json()
        return jsonify({'success': True, 'order_id': order['id'], 'amount': balance_amount})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/verify-balance-payment', methods=['POST'])
def verify_balance_payment():
    data = request.json
    try:
        # Update the booking in DB
        supabase.table('appointments').update({
            'balance_paid': True,
            'status': 'finished' # Mark as finished once balance is paid online
        }).eq('id', data.get('booking_id')).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/verify-payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    try:
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }
        if not verify_razorpay_signature(params_dict):
            raise Exception("Invalid Signature")

        supabase.table('appointments').insert({
            'user_id': session['user_id'],
            'service_id': data.get('service_id'),
            'date': data.get('date'),
            'time': data.get('time'),
            'staff_id': data.get('staff_id'),
            'status': 'pending',
            'payment_id': data.get('razorpay_payment_id'),
            'order_id': data.get('razorpay_order_id'),
            'is_paid': True,
            'payment_amount': 50.00
        }).execute()
        return jsonify({'success': True})
    except Exception as e:
        if 'staff_time_unique' in str(e):
            return jsonify({'success': False, 'message': 'Slot taken. Choose another specialist.'}), 409
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/update-status', methods=['POST'])
def update_booking_status():
    if not is_logged_in() or session.get('role') not in ['admin', 'staff']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.json
    booking_id = data.get('id')
    new_status = data.get('status')
    
    try:
        supabase.table('appointments').update({'status': new_status}).eq('id', booking_id).execute()
        return jsonify({'success': True, 'message': f'Status updated to {new_status}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/reschedule', methods=['POST'])
def reschedule_booking():
    if not is_logged_in() or session.get('role') not in ['admin', 'staff']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.json
    booking_id = data.get('id')
    new_date = data.get('date')
    new_time = data.get('time')
    
    try:
        # Check if rescheduling is within 1 hour limit (optional server-side check)
        # For simplicity, we just update the DB as per staff request
        supabase.table('appointments').update({
            'date': new_date,
            'time': new_time,
            'status': 'pending'  # Reset to pending for re-approval
        }).eq('id', booking_id).execute()
        return jsonify({'success': True, 'message': 'Slot rescheduled and reset to pending.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-staff', methods=['POST'])
def add_staff():
    if not is_logged_in() or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data = request.get_json()
    try:
        hashed = hash_password(data.get('password'))
        supabase.table('users').insert({
            'name': data.get('name'),
            'email': data.get('email'),
            'password': hashed,
            'role': 'staff',
            'gender': 'male' # Default
        }).execute()
        return jsonify({'success': True, 'message': 'Staff added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-service', methods=['POST'])
def add_service():
    if not is_logged_in() or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data = request.get_json()
    try:
        supabase.table('services').insert({
            'name': data.get('name'),
            'price': float(data.get('price')),
            'gender': data.get('gender'),
            'duration': 30,
            'description': data.get('description', 'Newly added service')
        }).execute()
        return jsonify({'success': True, 'message': 'Service added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/available-slots')
def available_slots():
    date = request.args.get('date')
    service_id = request.args.get('service_id')
    booked = supabase.table('appointments').select('time').eq('service_id', service_id).eq('date', date).eq('status', 'confirmed').execute()
    booked_times = [b['time'] for b in booked.data]
    all_slots = [f"{h:02d}:00" for h in range(9, 18)]
    available = [s for s in all_slots if s not in booked_times]
    return jsonify({'success': True, 'slots': available})

@app.route('/api/available-staff')
def get_available_staff():
    date = request.args.get('date')
    time = request.args.get('time')
    try:
        # Get all staff
        all_staff = supabase.table('users').select('id, name').eq('role', 'staff').execute()
        
        # Safe fetch for busy staff (handle missing column)
        try:
            busy = supabase.table('appointments').select('staff_id').eq('date', date).eq('time', time).eq('status', 'confirmed').execute()
            busy_ids = [b['staff_id'] for b in busy.data]
        except:
            # Column likely missing or table issues
            busy_ids = []
        
        available = [s for s in all_staff.data if s['id'] not in busy_ids]
        return jsonify({'success': True, 'staff': available})
    except Exception as e:
        print(f"STAFF FETCH ERROR: {e}")
        return jsonify({'success': False, 'message': 'Specialist tracking currently unavailable', 'staff': []})

@app.route('/booking-confirmation')
def booking_confirmation():
    return render_template('booking-confirmation.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)