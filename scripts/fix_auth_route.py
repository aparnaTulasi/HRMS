import os

auth_content = """from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import secrets
from sqlalchemy.exc import IntegrityError
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from config import Config
from utils.url_generator import generate_login_url, clean_username

auth_bp = Blueprint('auth', __name__)

# Invalid email domains
INVALID_DOMAINS = [
    'yahoo.com', 'outlook.com', 'hotmail.com', 'rediffmail.com',
    'protonmail.com', 'gmx.com', 'aol.com', 'mail.com'
]

VALID_COMPANY_DOMAINS = [
    'tectoro.com', 'tcs.com', 'infosys.com', 'wipro.com', 'accenture.com',
    'capgemini.com', 'hcl.com', 'techmahindra.com'
]

def validate_email_domain(email):
    if '@' not in email:
        return False, 'Invalid email format'
    domain = email.split('@')[1].lower()
    if domain in INVALID_DOMAINS:
        return False, f'@{domain} emails are not allowed'
    return True, 'Valid email'

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    is_valid, message = validate_email_domain(data['email'])
    if not is_valid:
        return jsonify({'message': message, 'allowed_domains': ['gmail.com'] + VALID_COMPANY_DOMAINS}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 409

    role = data.get('role')
    company_id = None
    company = None
    
    if role != 'SUPER_ADMIN':
        company_subdomain = data.get('company_subdomain')
        if not company_subdomain:
            return jsonify({'message': 'Company subdomain required'}), 400
        company = Company.query.filter_by(subdomain=company_subdomain).first()
        if not company:
            if role == 'ADMIN':
                company = Company(company_name=data.get('company_name', 'New Company'), subdomain=company_subdomain)
                db.session.add(company)
                db.session.flush()
            else:
                return jsonify({'message': 'Company not found'}), 404
        company_id = company.id
    
    otp = None
    otp_expiry = None
    status = 'ACTIVE' if role in ['SUPER_ADMIN', 'ADMIN', 'HR'] else 'PENDING_OTP'
    
    if status == 'PENDING_OTP':
        otp = ''.join(secrets.choice('0123456789') for _ in range(6))
        otp_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(
        email=data['email'], password=hashed_password, role=role,
        company_id=company_id, status=status, portal_prefix='aparna',
        otp=otp, otp_expiry=otp_expiry
    )
    db.session.add(new_user)
    db.session.flush()
    
    if role != 'SUPER_ADMIN' and company:
        new_employee = Employee(
            user_id=new_user.id, company_id=company.id,
            first_name=data.get('first_name'), last_name=data.get('last_name'),
            phone=data.get('phone'), department=data.get('department', role),
            designation=data.get('designation', role), date_of_joining=data.get('date_of_joining'),
            Salary=data.get('salary')
        )
        db.session.add(new_employee)

    try:
        db.session.commit()
        response_data = {'message': 'Registration successful', 'user_id': new_user.id, 'status': status, 'email': data['email']}
        if status == 'PENDING_OTP':
            response_data['otp'] = otp
            response_data['message'] += '. Use OTP for verification.'
        return jsonify(response_data), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'User might already exist'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if 'email' not in data or 'password' not in data: return jsonify({'message': 'Email and password required'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']): return jsonify({'message': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user_id': user.id, 'email': user.email, 'role': user.role,
        'company_id': user.company_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")
    return jsonify({'token': token, 'role': user.role, 'status': user.status, 'user_id': user.id, 'email': user.email, 'message': 'Login successful'})
"""

with open(os.path.join('routes', 'auth.py'), 'w', encoding='utf-8') as f:
    f.write(auth_content)

print("✅ routes/auth.py has been fixed.")