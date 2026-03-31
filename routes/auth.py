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
from utils.audit_logger import log_action

from utils.decorators import token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/super-admin/signup', methods=['POST'])
def super_admin_signup():
    print("🔹 Received /super-admin/signup request", flush=True)
    data = request.get_json(silent=True)
    print(f"🔹 Payload: {data}", flush=True)

    try:
        if not data:
            return jsonify({'message': 'Invalid JSON or Content-Type header'}), 400

        if not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Email and password are required'}), 400

        email = data['email'].lower().strip()
        
        # Check both User and SuperAdmin tables
        if User.query.filter_by(email=email).first() or SuperAdmin.query.filter_by(email=email).first():
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
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Signup Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Internal Server Error', 'error': str(e)}), 500

@auth_bp.route('/super-admin/verify-otp', methods=['POST'])
def verify_super_admin_otp():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'message': 'Request body is missing'}), 400

        otp = str(data.get('otp', '')).strip()

        if not otp:
            return jsonify({'message': 'OTP is required'}), 400

        # Try to find by email if provided, otherwise by OTP
        if data.get('email'):
            email = data.get('email').lower().strip()
            sa = SuperAdmin.query.filter_by(email=email).first()
        else:
            sa = SuperAdmin.query.filter_by(signup_otp=otp).first()

        if not sa:
            return jsonify({'message': 'Invalid OTP or User not found'}), 400
            
        if sa.signup_otp != otp:
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

@auth_bp.route('/verify-signup-otp', methods=['POST'])
def verify_signup_otp():
    print("🔹 Received /verify-signup-otp request", flush=True)
    data = request.get_json(silent=True) or {}
    print(f"🔹 Payload received: {data}", flush=True)

    if not data:
        return jsonify({'message': 'Invalid or missing JSON body. Check Content-Type header.'}), 400

    if not data.get('otp'):
        return jsonify({'message': 'OTP is required'}), 400

    otp = str(data['otp']).strip()

    # 1. Try to find user by OTP in User table (Regular Employees)
    user = User.query.filter_by(otp=otp).first()
    sa = None

    # 2. If not found, try to find in SuperAdmin table
    if not user:
        sa = SuperAdmin.query.filter_by(signup_otp=otp).first()
        if sa:
            user = User.query.get(sa.user_id)

    if not user:
        return jsonify({'message': 'Invalid OTP'}), 400

    if user.status and user.status.upper() == 'ACTIVE':
        return jsonify({'message': 'User is already active'}), 200

    # Validate OTP Expiry
    if sa:
        if sa.signup_otp_expiry and sa.signup_otp_expiry < datetime.utcnow():
            return jsonify({'message': 'OTP has expired'}), 400
    else:
        if user.otp_expiry and user.otp_expiry < datetime.utcnow():
            return jsonify({'message': 'OTP has expired'}), 400

    if user.role == 'SUPER_ADMIN':
        user.status = 'ACTIVE'
        message = 'OTP verified. Super Admin account activated.'
        # Sync SuperAdmin record if exists
        if not sa:
            sa = SuperAdmin.query.filter_by(user_id=user.id).first()
            
        if sa:
            sa.is_verified = True
            sa.signup_otp = None
            sa.signup_otp_expiry = None
    else:
        user.status = 'PENDING'
        message = 'OTP verified. Waiting for admin approval.'

    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': message, 'status': user.status}), 200

@auth_bp.route('/resend-signup-otp', methods=['POST'])
def resend_signup_otp():
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

    if user.status and user.status.upper() == 'ACTIVE':
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

@auth_bp.route('/resend-reset-otp', methods=['POST'])
def resend_reset_otp():
    data = request.get_json(silent=True) or {}
    if not data or not data.get('email'):
        return jsonify({'message': 'Email is required'}), 400

    email = data['email'].lower().strip()
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    otp = user.generate_otp()
    db.session.commit()

    if send_password_reset_otp(email, otp):
        return jsonify({'message': 'Reset OTP resent successfully'}), 200
    else:
        return jsonify({'message': 'Failed to send OTP email'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    company = None
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

    if user.status and user.status.upper() != 'ACTIVE':
        return jsonify({'message': f'Your account status is {user.status}. Please contact support.'}), 403

    if hasattr(user, 'is_active') and user.is_active == False:
        return jsonify({'message': 'Your account has been deactivated. Please contact support.'}), 403

    # Check Company Status
    if user.role != 'SUPER_ADMIN' and user.company_id:
        company = Company.query.get(user.company_id)
        if company and company.status and company.status.upper() == 'INACTIVE':
            return jsonify({'message': 'Your company account has been deactivated. Please contact support.'}), 403

    employee = Employee.query.filter_by(user_id=user.id).first()

    token = jwt.encode({
        'user_id': user.id,
        'role': user.role,
        'company_id': user.company_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")

    # Audit Log
    g.user = user
    log_action("LOGIN", "User", user.id, 200)

    user_data = {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'name': user.name,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None,
    }

    # Determine Redirect URL
    base_url = build_company_base_url("")
    
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
        'name': user.name,
        'company_id': user.company_id,
        'company_name': company.company_name if company else None,
    }

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

    user = None
    # 1. Try to decode JWT reset_token
    print(f"DEBUG: reset_token={reset_token[:10]}... email={data.get('email')} otp={data.get('otp')}")
    try:
        payload = jwt.decode(
            reset_token,
            current_app.config['SECRET_KEY'],
            algorithms=["HS256"]
        )
        print(f"DEBUG: JWT Decoded! payload={payload}")
        if payload.get('type') == 'password_reset':
            user = User.query.get(payload['user_id'])
    except Exception as e:
        print(f"DEBUG: JWT Decode FAILED: {str(e)}")
        # 2. Fallback: Check if reset_token is a valid OTP OR if otp is explicitly provided
        email = data.get('email', '').lower().strip()
        otp_candidate = data.get('otp') or reset_token
        print(f"DEBUG: FALLBACK checking email={email} otp_candidate={otp_candidate}")
        if email and otp_candidate:
            user = User.query.filter_by(email=email, otp=str(otp_candidate)).first()
            if user:
                print(f"DEBUG: User found by OTP! expiry={user.otp_expiry}")
            if user and user.otp_expiry and user.otp_expiry < datetime.utcnow():
                print(f"DEBUG: OTP EXPIRED! now={datetime.utcnow()}")
                user = None # OTP expired

    if not user:
        print(f"DEBUG: FINAL NO USER FOUND!")
        return jsonify({'message': 'Invalid reset token or OTP'}), 401

    try:
        user.password = generate_password_hash(new_password)
        user.otp = None # Clear OTP after use
        user.otp_expiry = None
        db.session.commit()
        return jsonify({'message': 'Password has been reset successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Error updating password: {str(e)}'}), 500

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