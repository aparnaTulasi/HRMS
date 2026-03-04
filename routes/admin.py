from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from models import db
from models.user import User
from sqlalchemy import inspect, func
from sqlalchemy.exc import IntegrityError
from models.employee import Employee
from models.company import Company
from utils.decorators import token_required, role_required
from datetime import datetime
import re

admin_bp = Blueprint('admin', __name__)

def _set_if_exists(obj, field, value):
    if value is None:
        return
    if hasattr(obj, field):
        setattr(obj, field, value)

def generate_employee_id(company_code: str) -> str:
    # get last employee_id for that company like TC001-0009
    last_id = (
        db.session.query(Employee.employee_id)
        .filter(Employee.employee_id.like(f"{company_code}-%"))
        .order_by(Employee.employee_id.desc())
        .first()
    )

    if not last_id or not last_id[0]:
        return f"{company_code}-0001"

    m = re.search(r"-(\d+)$", last_id[0])
    last_num = int(m.group(1)) if m else 0
    new_num = last_num + 1
    return f"{company_code}-{new_num:04d}"

@admin_bp.route('/create-manager', methods=['POST'])
@admin_bp.route('/create-employee', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN'])
def create_employee():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    # 1. Validate Passwords
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    if not password or not confirm_password:
        return jsonify({'message': 'Password and Confirm Password are required'}), 400
    if password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400

    # 2. Identify Company
    # Payload sends "company_id": "TC001" (string code)
    req_company_id = data.get('company_id')
    company = None

    if g.user.role == 'SUPER_ADMIN':
        if not req_company_id:
            return jsonify({'message': 'Company ID/Code is required for Super Admin'}), 400
        
        # Try finding by code first
        company = Company.query.filter_by(company_code=req_company_id).first()
        # Fallback to ID if numeric
        if not company and str(req_company_id).isdigit():
            company = Company.query.get(int(req_company_id))
            
        if not company:
            return jsonify({'message': f'Company not found with identifier: {req_company_id}'}), 404
    else:
        # ADMIN can only create for their own company
        company = Company.query.get(g.user.company_id)
        if not company:
            return jsonify({'message': 'Admin company context not found'}), 404

    # 3. Check Email Uniqueness
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Email is required'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400

    # 4. Determine Role
    designation = data.get('designation', '').strip()
    role = 'EMPLOYEE'
    
    # Map designation to role
    designation_lower = designation.lower()
    if 'manager' in designation_lower:
        role = 'MANAGER'
    elif 'hr' in designation_lower:
        role = 'HR'
    elif 'admin' in designation_lower:
        role = 'ADMIN'
    
    # 5. Create User Account
    hashed_password = generate_password_hash(password)
    new_user = User(
        email=email,
        password=hashed_password,
        role=role,
        company_id=company.id,
        status='ACTIVE'
    )
    db.session.add(new_user)
    db.session.flush() # Generate ID

    # 6. Generate Employee ID
    if company.last_user_number is None:
        company.last_user_number = 0
    company.last_user_number += 1
    
    # Use company_code as the primary prefix for consistency with the request identifier.
    prefix = company.company_code or company.company_prefix or "EMP"
    new_emp_id = generate_employee_id(prefix)

    # 7. Create Employee Profile
    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        return jsonify({"success": False, "message": "full_name is required"}), 400

    new_employee = Employee(
        user_id=new_user.id,
        company_id=g.user.company_id,
        employee_id=data.get('employee_id') or new_emp_id,
        full_name=data['full_name'],
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=datetime.strptime(data['date_of_joining'], '%Y-%m-%d').date() if data.get('date_of_joining') else None,
        gender=data.get('gender'),
        personal_email=data.get('personal_email'),

        # ✅ IMPORTANT
        phone_number=data.get('phone_number'),
        company_email=data.get('email')
    )
    
    try:
        db.session.add(new_employee)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        db.session.add(new_user) # Re-add user as rollback removed it from session
        new_employee.employee_id = generate_employee_id(prefix)
        db.session.add(new_employee)
        db.session.commit()

    return jsonify({
        'message': f'{designation or role} created successfully',
        'employee_id': new_employee.employee_id,
        'company_email': getattr(new_employee, 'company_email', email),
        'email_sent': True,
        'personal_email': getattr(new_employee, 'personal_email', None)
    }), 201