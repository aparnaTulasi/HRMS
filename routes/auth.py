from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from datetime import datetime, timedelta
from config import Config
import secrets
from models import db
from models.user import User
from models.super_admin import SuperAdmin
from models.employee import Employee
from models.company import Company
from utils.email_utils import send_account_created_alert, send_login_credentials, send_signup_otp, send_password_reset_otp
from utils.url_generator import build_company_base_url

from utils.decorators import token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/super-admin/signup', methods=['POST'])
def super_admin_signup():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required'}), 400

    email = data['email'].lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400

    hashed_password = generate_password_hash(data['password'])

    # 1. Create User (Inactive initially)
    user = User(
        email=email,
        password=hashed_password,
        role='SUPER_ADMIN',
        status='PENDING'
    )
    db.session.add(user)
    db.session.flush() # Flush to get user.id

    # 2. Create SuperAdmin Profile with OTP
    sa = SuperAdmin(
        user_id=user.id,
        email=email,
        password=hashed_password,
        first_name=data.get('first_name'),
        last_name=data.get('last_name')
    )
    otp = sa.generate_signup_otp()
    db.session.add(sa)

    db.session.commit()

    if send_signup_otp(email, otp):
        return jsonify({'message': 'Signup successful. OTP sent to email.'}), 201
    else:
        return jsonify({'message': 'Signup successful, but failed to send OTP email.'}), 201

@auth_bp.route('/super-admin/verify-otp', methods=['POST'])
def verify_super_admin_otp():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is missing'}), 400

        email = data.get('email')
        otp = str(data.get('otp', '')).strip()

        if not email or not otp:
            return jsonify({'message': 'Email and OTP are required'}), 400

        email = email.lower().strip()
        sa = SuperAdmin.query.filter_by(email=email).first()

        if not sa or sa.signup_otp != otp:
            return jsonify({'message': 'Invalid OTP'}), 400
        
        if sa.signup_otp_expiry and sa.signup_otp_expiry < datetime.utcnow():
            return jsonify({'message': 'OTP has expired'}), 400

        sa.is_verified = True
        sa.signup_otp = None  # Clear OTP
        User.query.filter_by(id=sa.user_id).update({'status': 'ACTIVE'})
        db.session.commit()

        return jsonify({'message': 'Account verified successfully. You can now login.'}), 200
    except Exception as e:
        print(f"Error in verify-otp: {e}")
        return jsonify({'message': 'Internal Server Error', 'error': str(e)}), 500

@auth_bp.route('/verify-signup-otp', methods=['POST', 'OPTIONS'])
def verify_signup_otp():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    print("🔹 Received /verify-signup-otp request", flush=True)
    data = request.get_json(silent=True) or {}
    if not data or not data.get('email') or not data.get('otp'):
        return jsonify({'message': 'Email and OTP are required'}), 400

    email = data['email'].lower().strip()
    otp = str(data['otp']).strip()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if user.status == 'ACTIVE':
        return jsonify({'message': 'User is already active'}), 200

    if user.otp != otp:
        return jsonify({'message': 'Invalid OTP'}), 400
        
    if user.otp_expiry and user.otp_expiry < datetime.utcnow():
        return jsonify({'message': 'OTP has expired'}), 400

    user.status = 'PENDING'
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': 'OTP verified. Waiting for admin approval.', 'status': 'PENDING'}), 200

@auth_bp.route('/resend-signup-otp', methods=['POST', 'OPTIONS'])
def resend_signup_otp():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    data = request.get_json(silent=True) or {}
    if not data or not data.get('email'):
        return jsonify({'message': 'Email is required'}), 400

    email = data['email'].lower().strip()

    # 1. Check Super Admin
    sa = SuperAdmin.query.filter_by(email=email).first()
    if sa:
        if sa.is_verified:
            return jsonify({'message': 'Account already verified'}), 400
        
        otp = sa.generate_signup_otp()
        db.session.commit()
        
        if send_signup_otp(email, otp):
            return jsonify({'message': 'OTP resent successfully'}), 200
        else:
            return jsonify({'message': 'Failed to send OTP email. Check server logs.'}), 500

    # 2. Check Regular User
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if user.status == 'ACTIVE':
        return jsonify({'message': 'Account already active'}), 400

    # Generate OTP
    otp = ''.join(secrets.choice('0123456789') for _ in range(6))
    user.otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    if send_signup_otp(email, otp):
        return jsonify({'message': 'OTP resent successfully'}), 200
    else:
        return jsonify({'message': 'Failed to send OTP email. Check server logs.'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required'}), 400

    email = data['email'].lower().strip()
    password = data['password']

    print(f"🔐 Login Attempt for: {email}")  # Debug log

    user = User.query.filter_by(email=email).first()

    if not user:
        print(f"❌ Login Failed: User not found for {email}")  # Debug log
        return jsonify({'message': 'Invalid credentials'}), 401
    
    print(f"   🔍 Found User: ID={user.id}, Role={user.role}, Status={user.status}")

    if not check_password_hash(user.password, password):
        print(f"❌ Login Failed: Password mismatch for {email}")  # Debug log
        return jsonify({'message': 'Invalid credentials'}), 401

    if user.status != 'ACTIVE':
        return jsonify({'message': f'User account is {user.status}. Please verify your email or contact admin.'}), 403

    employee = Employee.query.filter_by(user_id=user.id).first()
    company = Company.query.filter_by(id=user.company_id).first()

    token = jwt.encode({
        'user_id': user.id,
        'role': user.role,
        'company_id': user.company_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")

    user_data = {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None,
        'subdomain': company.subdomain if company else None,
    }
    if employee:
        user_data.update({
            'employee_id': employee.id,
            'employee_code': employee.employee_id,
            'employee_name': employee.full_name,
        })

    # Determine Redirect URL
    subdomain = company.subdomain if company else ""
    base_url = build_company_base_url(subdomain)
    
    role_paths = {
        "SUPER_ADMIN": "/super-admin/dashboard",
        "ADMIN": "/admin/dashboard",
        "HR": "/hr/dashboard",
        "EMPLOYEE": "/employee/dashboard",
        "MANAGER": "/employee/dashboard"
    }
    
    path = role_paths.get(user.role, "/dashboard")
    redirect_url = f"{base_url}{path}"

    return jsonify({
        'token': token,
        'user': user_data,
        'redirect_url': redirect_url
    })

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user = g.user
    employee = Employee.query.filter_by(user_id=user.id).first()
    company = Company.query.filter_by(id=user.company_id).first()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    user_data = {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None,
        'subdomain': company.subdomain if company else None,
    }
    if employee:
        user_data.update({
            'employee_id': employee.id,
            'employee_code': employee.employee_id,
            'employee_name': employee.full_name,
        })

    return jsonify(user_data), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'message': 'Email is required'}), 400

    email = data['email'].lower().strip()
    user = User.query.filter_by(email=email).first()

    if user:
        # The generate_otp method on the User model handles OTP creation and expiry
        otp = user.generate_otp()
        if otp:
            db.session.commit()
            try:
                # The app context is available in a request context
                send_password_reset_otp(user.email, otp)
            except Exception as e:
                # Log the error but don't expose details to the user
                current_app.logger.error(f"Failed to send password reset OTP email to {user.email}: {e}")
    
    # For security, always return a success message.
    # This prevents attackers from enumerating registered email addresses.
    return jsonify({'message': 'If an account with that email exists, a password reset OTP has been sent.'}), 200

@auth_bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    data = request.get_json()
    print(f"🔍 Verifying OTP for: {data.get('email')}", flush=True)
    if not data or not data.get('email') or not data.get('otp'):
        return jsonify({'message': 'Email and OTP are required'}), 400

    email = data['email'].lower().strip()
    user = User.query.filter_by(email=email).first()

    if not user or user.otp != str(data['otp']):
        return jsonify({'message': 'Invalid OTP or email'}), 400

    if not user.otp_expiry or user.otp_expiry < datetime.utcnow():
        return jsonify({'message': 'OTP has expired'}), 400

    # Generate a reset token for the next step
    reset_token = jwt.encode(
        {
            'user_id': user.id,
            'type': 'password_reset',
            'exp': datetime.utcnow() + timedelta(minutes=15)
        },
        current_app.config['SECRET_KEY'],
        algorithm="HS256"
    )

    # Invalidate the OTP so it can't be used again
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({
        'message': 'OTP verified successfully',
        'reset_token': reset_token
    }), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Step 3: User provides the reset_token and a new password.
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is required'}), 400

    reset_token = data.get('reset_token')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not reset_token or not new_password:
        return jsonify({'message': 'Reset token and new password are required'}), 400

    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400

    try:
        payload = jwt.decode(
            reset_token,
            current_app.config['SECRET_KEY'],
            algorithms=["HS256"]
        )

        if payload.get('type') != 'password_reset':
            return jsonify({'message': 'Invalid token type'}), 401

        user_id = payload['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({'message': 'User not found'}), 404

        user.password = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({'message': 'Password has been reset successfully'}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Reset token has expired. Please start over.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid reset token'}), 401

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """
    Allows an authenticated user to change their own password.
    """
    user = g.user # User from @token_required decorator
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not all([current_password, new_password, confirm_password]):
        return jsonify({'message': 'Current password, new password, and confirmation are required'}), 400

    if not check_password_hash(user.password, current_password):
        return jsonify({'message': 'Invalid current password'}), 403

    if new_password != confirm_password:
        return jsonify({'message': 'New passwords do not match'}), 400

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({'message': 'Password changed successfully'}), 200