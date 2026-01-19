from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
import secrets
import string
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required
from utils.email_utils import send_login_credentials

superadmin_bp = Blueprint('superadmin', __name__)

def generate_company_code(name):
    clean = ''.join(ch for ch in name if ch.isalnum())
    prefix = (clean[:2] or "CO").upper()
    suffix = ''.join(secrets.choice(string.digits) for _ in range(2))
    return f"{prefix}{suffix}"


@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json()

    required = ["company_name", "subdomain", "admin_email"]
    if not data or not all(data.get(k) for k in required):
        return jsonify({"message": "company_name, subdomain, admin_email are required"}), 400

    # Check if admin email already exists
    if User.query.filter_by(email=data['admin_email']).first():
        return jsonify({'message': 'Admin email already exists'}), 409

    # Generate or use provided company code
    company_code = data.get('company_code') or generate_company_code(data['company_name'])
    
    try:
        new_company = Company(
            company_name=data['company_name'], 
            subdomain=data['subdomain'],
            company_code=company_code
        )
        db.session.add(new_company)
        db.session.flush()

        # Generate random password for Admin
        raw_password = secrets.token_urlsafe(12)
        hashed_password = generate_password_hash(raw_password, method='pbkdf2:sha256')
        
        new_admin = User(email=data['admin_email'], password=hashed_password, role='ADMIN', company_id=new_company.id)
        db.session.add(new_admin)
        db.session.flush()

        admin_emp = Employee(user_id=new_admin.id, company_id=new_company.id, first_name=data.get('admin_first_name', 'Admin'), last_name=data.get('admin_last_name', 'User'))
        db.session.add(admin_emp)
        db.session.commit()
        
        # Send Email with Credentials and URL
        username = data['admin_email'].split('@')[0]
        login_url = f"http://{username}{company_code}.{data['subdomain']}"
        
        email_sent = send_login_credentials(data['admin_email'], raw_password, login_url)
        
        return jsonify({
            'message': 'Company and Admin created', 
            'company_code': company_code,
            'email_sent': email_sent
        }), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'Database integrity error (possibly duplicate Company Code)', 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred', 'error': str(e)}), 500

@superadmin_bp.route('/create-admin', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_admin():
    data = request.get_json()
    
    # 1. Find Company
    company_id = data.get('company_id')
    if not company_id and data.get('subdomain'):
        company = Company.query.filter_by(subdomain=data['subdomain']).first()
        if company:
            company_id = company.id
            
    if not company_id:
        return jsonify({'message': 'Company not found. Provide valid company_id or subdomain.'}), 404
        
    company = Company.query.get(company_id)
    
    # 2. Check if Admin already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User with this email already exists'}), 409
        
    # 3. Create Admin User
    raw_password = secrets.token_urlsafe(12)
    hashed_password = generate_password_hash(raw_password, method='pbkdf2:sha256')
    
    new_admin = User(email=data['email'], password=hashed_password, role='ADMIN', company_id=company_id, is_active=True)
    db.session.add(new_admin)
    db.session.flush()
    
    # 4. Create Employee Profile
    admin_emp = Employee(
        user_id=new_admin.id,
        company_id=company_id,
        first_name=data.get('first_name', 'Admin'),
        last_name=data.get('last_name', 'User'),
        department='Management',
        designation='Admin',
        date_of_joining=datetime.utcnow()
    )
    db.session.add(admin_emp)
    db.session.commit()
    
    # 5. Send Email
    username = data['email'].split('@')[0]
    code = company.company_code if company.company_code else "00"
    login_url = f"http://{username}{code}.{company.subdomain}"
    
    send_login_credentials(data['email'], raw_password, login_url)
    
    return jsonify({'message': 'Admin created successfully', 'email': data['email']}), 201

@superadmin_bp.route('/users', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_user():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 409
        
    company_id = data.get('company_id')
    if not company_id:
        return jsonify({'message': 'Company ID is required'}), 400
        
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'message': 'Company not found'}), 404

    role = data.get('role', 'EMPLOYEE')
    
    # Generate Credentials
    raw_password = secrets.token_urlsafe(12)
    hashed_password = generate_password_hash(raw_password, method='pbkdf2:sha256')
    
    new_user = User(
        email=data['email'],
        password=hashed_password,
        role=role,
        company_id=company_id,
        is_active=True
    )
    db.session.add(new_user)
    db.session.flush()
    
    new_employee = Employee(
        user_id=new_user.id,
        company_id=company_id,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        department=data.get('department'),
        designation=data.get('designation', role),
        date_of_joining=data.get('date_of_joining')
    )
    db.session.add(new_employee)
    db.session.commit()
    
    # Email
    username = data['email'].split('@')[0]
    code = company.company_code if company.company_code else "00"
    domain = company.subdomain
    login_url = f"http://{username}{code}.{domain}"
    
    send_login_credentials(data['email'], raw_password, login_url)
    
    return jsonify({'message': f'User ({role}) created successfully'}), 201

@superadmin_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
@role_required(['SUPER_ADMIN'])
def update_user(user_id):
    data = request.get_json()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    if 'role' in data:
        user.role = data['role']
    if 'is_active' in data:
        user.is_active = data['is_active']
    if 'email' in data:
        user.email = data['email']
        
    employee = Employee.query.filter_by(user_id=user.id).first()
    if employee:
        if 'first_name' in data: employee.first_name = data['first_name']
        if 'last_name' in data: employee.last_name = data['last_name']
        if 'department' in data: employee.department = data['department']
        if 'designation' in data: employee.designation = data['designation']
        
    db.session.commit()
    return jsonify({'message': 'User updated successfully'}), 200

@superadmin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@role_required(['SUPER_ADMIN'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    Employee.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200