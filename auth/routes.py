from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from sqlalchemy.exc import IntegrityError
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User with this email already exists'}), 409

    role = data.get('role')
    company_id = None
    company = None
    
    if role != 'SUPER_ADMIN':
        company_subdomain = data.get('company_subdomain')
        if not company_subdomain:
            return jsonify({'message': 'company_subdomain is required for non-Super-Admin roles'}), 400
        
        company = Company.query.filter_by(subdomain=company_subdomain).first()
        
        if not company:
            if role == 'ADMIN':
                company = Company(company_name=data.get('company_name', 'Default Company'), subdomain=company_subdomain)
                db.session.add(company)
                db.session.commit()
            else: # For EMPLOYEE or HR
                return jsonify({'message': 'Company not found!'}), 404
        
        company_id = company.id

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    # Determine status
    status = 'ACTIVE' if role in ['SUPER_ADMIN', 'ADMIN'] else 'PENDING'
    
    new_user = User(
        email=data['email'],
        password=hashed_password,
        role=role,
        company_id=company_id,
        status=status,
        portal_prefix='aparna' # As per user request
    )
    
    # If Employee or Admin, create employee profile shell
    if role in ['EMPLOYEE', 'ADMIN'] and company:
        new_employee = Employee(
            user_id=new_user.id,
            company_id=company.id,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            phone=data.get('phone'),
            department=data.get('department'),
            designation=data.get('designation'),
            date_of_joining=data.get('date_of_joining')
        )
        db.session.add(new_employee)

    db.session.add(new_user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'An error occurred. A user with this email might already exist.'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Could not create user.', 'error': str(e)}), 500

    if status == 'PENDING':
        return jsonify({
            'message': 'Registration successful. Waiting for admin approval', 
            'status': 'PENDING'
        }), 201

    return jsonify({
        'message': 'User registered successfully!',
        'status': 'ACTIVE'
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
        
    if user.status == 'PENDING':
        return jsonify({'message': 'Approval pending. Please contact your administrator.'}), 403

    if user.status != 'ACTIVE':
        return jsonify({'message': 'Account is not active. Please contact Admin.'}), 403
        
    token = jwt.encode({
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'company_id': user.company_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")
    
    prefix = user.portal_prefix or "default"

    if user.role == 'SUPER_ADMIN':
        redirect_url = f"https://{prefix}/superadmin.portal.com"
    elif user.company:
        subdomain = user.company.subdomain
        redirect_url = f"https://{prefix}/{subdomain}.hrms.com/{user.role.lower()}"
    else:
        redirect_url = '/dashboard'
    
    return jsonify({
        'token': token,
        'role': user.role,
        'redirect_url': redirect_url
    })