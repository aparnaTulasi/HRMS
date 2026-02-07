from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocument
from models.user import User
from utils.decorators import token_required, role_required
import os
from config import Config
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from datetime import datetime

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Profile not found'}), 404
    
    addresses = []
    for addr in emp.addresses:
        addresses.append({
            'type': addr.address_type,
            'line1': addr.address_line1,
            'line2': addr.address_line2,
            'city': addr.city,
            'state': addr.state,
            'zip_code': addr.zip_code,
            'country': addr.country
        })

    return jsonify({
        'id': emp.id,
        'employee_id': emp.employee_id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'email': emp.company_email,
        'personal_email': emp.personal_email,
        'department': emp.department,
        'designation': emp.designation,
        'salary': emp.salary,
        'phone': getattr(emp, 'work_phone', None),
        'date_of_joining': emp.date_of_joining.isoformat() if emp.date_of_joining else None,
        'addresses': addresses
    })

@employee_bp.route('/create', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_employee():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 400
        
    hashed_password = generate_password_hash(data.get('password', 'Password@123'), method='pbkdf2:sha256')
    new_user = User(
        email=data['email'],
        password=hashed_password,
        role=data.get('role', 'EMPLOYEE'),
        company_id=g.user.company_id,
        status='ACTIVE'
    )
    db.session.add(new_user)
    db.session.flush()
    
    new_emp = Employee(
        user_id=new_user.id,
        company_id=g.user.company_id,
        employee_id=data.get('employee_id'),
        first_name=data['first_name'],
        last_name=data['last_name'],
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=datetime.strptime(data['date_of_joining'], '%Y-%m-%d').date() if data.get('date_of_joining') else None,
        gender=data.get('gender'),
        personal_email=data.get('personal_email'),
        work_phone=data.get('work_phone')
    )
    db.session.add(new_emp)
    db.session.commit()
    
    return jsonify({'message': 'Employee created successfully', 'employee_id': new_emp.id}), 201

@employee_bp.route('/<int:id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_employee(id):
    emp = Employee.query.get_or_404(id)
    if emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    if 'first_name' in data: emp.first_name = data['first_name']
    if 'last_name' in data: emp.last_name = data['last_name']
    if 'department' in data: emp.department = data['department']
    if 'designation' in data: emp.designation = data['designation']
    if 'work_phone' in data: emp.work_phone = data['work_phone']
    if 'personal_mobile' in data: emp.personal_mobile = data['personal_mobile']
    if 'personal_email' in data: emp.personal_email = data['personal_email']
    if 'date_of_birth' in data and data['date_of_birth']: 
        emp.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
    
    db.session.commit()
    return jsonify({'message': 'Employee updated successfully'})

@employee_bp.route('/address', methods=['POST'])
@token_required
def add_address():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID required'}), 400

    address = EmployeeAddress.query.filter_by(employee_id=emp_id).first()
    if not address:
        address = EmployeeAddress(employee_id=emp_id)
        db.session.add(address)
        
    address.address_line1 = data.get('address_line1')
    address.permanent_address = data.get('permanent_address')
    address.city = data.get('city')
    address.state = data.get('state')
    address.zip_code = data.get('zip_code')
    
    db.session.commit()
    return jsonify({'message': 'Address updated successfully'})

@employee_bp.route('/bank', methods=['POST'])
@token_required
def add_bank_details():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID required'}), 400
    
    bank = EmployeeBankDetails.query.filter_by(employee_id=emp_id).first() or EmployeeBankDetails(employee_id=emp_id)
    if not bank.id: db.session.add(bank)
    
    bank.bank_name = data.get('bank_name')
    bank.account_number = data.get('account_number')
    bank.ifsc_code = data.get('ifsc_code')
    bank.branch_name = data.get('branch_name')
    
    # Update Statutory details on Employee model
    emp = Employee.query.get(emp_id)
    if emp:
        if 'pan_number' in data: emp.pan_number = data['pan_number']
        if 'aadhaar_number' in data: emp.aadhaar_number = data['aadhaar_number']
    
    db.session.commit()
    return jsonify({'message': 'Bank and statutory details updated successfully'})