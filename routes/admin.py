from flask import Blueprint, jsonify, g
from flask import request
from werkzeug.security import generate_password_hash
import secrets
from utils.decorators import token_required, role_required
from models.employee import Employee
from models.user import User
from models import db
from utils.email_utils import send_login_credentials

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([{'id': emp.id, 'name': f"{emp.first_name} {emp.last_name}"} for emp in employees])

@admin_bp.route('/employees', methods=['POST'])
@token_required
@role_required(['ADMIN'])
def create_employee():
    data = request.get_json(force=True)
    
    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User with this email already exists'}), 409

    # Generate Credentials
    raw_password = secrets.token_urlsafe(10)
    hashed_password = generate_password_hash(raw_password, method='pbkdf2:sha256')
    
    # Create User Record
    role = data.get('role', 'EMPLOYEE')
    if role == 'SUPER_ADMIN':
        return jsonify({'message': 'Cannot create Super Admin'}), 403

    new_user = User(
        email=data['email'],
        password=hashed_password,
        role=role,
        company_id=g.user.company_id,
        is_active=True
    )
    db.session.add(new_user)
    db.session.flush()

    # Create Employee Record
    new_employee = Employee(
        user_id=new_user.id,
        company_id=g.user.company_id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=data.get('date_of_joining')
    )
    db.session.add(new_employee)
    db.session.commit()

    # Construct URL and Send Email
    company = g.user.company
    username = data['email'].split('@')[0]
    code = company.company_code if hasattr(company, 'company_code') and company.company_code else "00"
    domain = company.subdomain
    
    login_url = f"http://{username}{code}.{domain}"
    
    send_login_credentials(data['email'], raw_password, login_url)

    return jsonify({'message': 'Employee created and credentials sent via email'}), 201