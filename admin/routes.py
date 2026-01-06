from flask import Blueprint, jsonify, request, g
from models import db
from models.user import User
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from utils.decorators import token_required, role_required
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/approve-employee/<int:user_id>', methods=['POST'])
@token_required
@role_required(['ADMIN'])
def approve_employee(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    if user.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized access to this user'}), 403
        
    user.status = 'ACTIVE'
    db.session.commit()
    
    return jsonify({
        'message': 'Employee approved successfully',
        'status': 'ACTIVE'
    })

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    output = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        output.append({
            'id': emp.id,
            'user_id': emp.user_id,
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'email': user.email,
            'status': user.status,
            'department': emp.department,
            'designation': emp.designation
        })
    return jsonify({'employees': output})

@admin_bp.route('/pending-employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_pending_employees():
    users = User.query.filter_by(company_id=g.user.company_id, status='PENDING', role='EMPLOYEE').all()
    output = []
    for user in users:
        emp = Employee.query.filter_by(user_id=user.id).first()
        if emp:
            output.append({
                'user_id': user.id,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'email': user.email,
                'department': emp.department,
                'designation': emp.designation,
                'date_of_joining': emp.date_of_joining
            })
    return jsonify({'pending_employees': output})

@admin_bp.route('/create-hr', methods=['POST'])
@token_required
@role_required(['ADMIN'])
def create_hr():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists'}), 400
        
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    new_hr = User(
        email=data['email'],
        password=hashed_password,
        role='HR',
        company_id=g.user.company_id,
        status='ACTIVE',
        portal_prefix=g.user.portal_prefix # Inherit prefix from creating admin
    )
    db.session.add(new_hr)
    db.session.commit()
    
    new_emp = Employee(
        user_id=new_hr.id,
        company_id=g.user.company_id,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        department='HR',
        designation='HR Manager'
    )
    db.session.add(new_emp)
    db.session.commit()
    
    return jsonify({'message': 'HR created successfully'}), 201

@admin_bp.route('/employee/<int:emp_id>', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_single_employee(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp or emp.company_id != g.user.company_id:
        return jsonify({'message': 'Employee not found'}), 404
        
    user = User.query.get(emp.user_id)
    
    return jsonify({
        'id': emp.id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'email': user.email,
        'phone': emp.phone,
        'department': emp.department,
        'designation': emp.designation,
        'date_of_joining': emp.date_of_joining
    })

@admin_bp.route('/employee/<int:emp_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_employee_basic(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp or emp.company_id != g.user.company_id:
        return jsonify({'message': 'Employee not found'}), 404
        
    data = request.get_json()
    if 'first_name' in data: emp.first_name = data['first_name']
    if 'last_name' in data: emp.last_name = data['last_name']
    if 'phone' in data: emp.phone = data['phone']
    if 'department' in data: emp.department = data['department']
    if 'designation' in data: emp.designation = data['designation']
    
    db.session.commit()
    return jsonify({'message': 'Employee updated successfully'})

@admin_bp.route('/employee/<int:emp_id>/bank', methods=['PUT'])
@token_required
@role_required(['ADMIN'])
def update_employee_bank(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp or emp.company_id != g.user.company_id:
        return jsonify({'message': 'Employee not found'}), 404
        
    data = request.get_json()
    bank = EmployeeBankDetails.query.filter_by(employee_id=emp.id).first()
    if not bank:
        bank = EmployeeBankDetails(employee_id=emp.id)
        db.session.add(bank)
        
    bank.bank_name = data.get('bank_name')
    bank.account_number = data.get('account_number')
    bank.ifsc_code = data.get('ifsc_code')
    
    db.session.commit()
    return jsonify({'message': 'Bank details updated'})

@admin_bp.route('/employee/<int:emp_id>/address', methods=['PUT'])
@token_required
@role_required(['ADMIN'])
def update_employee_address(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp or emp.company_id != g.user.company_id:
        return jsonify({'message': 'Employee not found'}), 404
        
    data = request.get_json()
    addr = EmployeeAddress.query.filter_by(employee_id=emp.id).first()
    if not addr:
        addr = EmployeeAddress(employee_id=emp.id)
        db.session.add(addr)
        
    addr.address_line1 = data.get('address_line1')
    addr.city = data.get('city')
    addr.state = data.get('state')
    addr.zip_code = data.get('zip_code')
    
    db.session.commit()
    return jsonify({'message': 'Address updated'})