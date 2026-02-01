from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import secrets
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from config import Config
from utils.email_utils import send_login_success_email, send_signup_otp
from utils.url_generator import build_company_base_url

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(email=data['email'], password=hashed_password, role=data.get('role', 'EMPLOYEE'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email') or data.get('company_email')
    if not email:
        return jsonify({'message': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    if user.status == 'PENDING_OTP':
        return jsonify({'message': 'OTP verification required', 'code': 'OTP_REQUIRED'}), 403

    token = jwt.encode({
        'user_id': user.id, 'email': user.email, 'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")
    
    try:
        send_login_success_email(user.email)
    except:
        pass

    # Determine Redirect URL
    ROLE_PATHS = {
        "SUPER_ADMIN": "/super/dashboard",
        "ADMIN": "/admin/dashboard",
        "HR": "/hr/dashboard",
        "EMPLOYEE": "/employee/dashboard",
    }
    
    company = Company.query.get(user.company_id) if user.company_id else None
    subdomain = company.subdomain if company else ""
    base_url = build_company_base_url(subdomain)
    path = ROLE_PATHS.get(user.role, "/")
    
    return jsonify({
        'token': token,
        'role': user.role,
        'redirect_url': f"{base_url}{path}"
    })

@auth_bp.route('/super-admin/signup', methods=['POST'])
def super_admin_signup():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(email=data['email'], password=hashed_password, role='SUPER_ADMIN', status='PENDING_OTP')
    
    # Generate OTP
    otp = new_user.generate_otp()
    
    send_signup_otp(data['email'], otp)
    db.session.add(new_user)
    db.session.flush()

    new_employee = Employee(
        user_id=new_user.id,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        employee_id=f"SA-{new_user.id}"
    )
    db.session.add(new_employee)
    db.session.commit()

    return jsonify({'message': 'Super Admin registered successfully. Please check your email for OTP.'}), 201

@auth_bp.route('/verify-signup-otp', methods=['POST'])
def verify_signup_otp():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    if user.otp != data.get('otp'):
        return jsonify({'message': 'Invalid OTP'}), 400
    if user.otp_expiry and user.otp_expiry < datetime.datetime.utcnow():
        return jsonify({'message': 'OTP expired'}), 400
        
    user.status = 'ACTIVE'
    user.otp = None
    user.otp_expiry = None
    db.session.commit()
    return jsonify({'message': 'Account verified successfully'}), 200