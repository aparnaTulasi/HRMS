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
import logging
from utils.email_utils import send_login_credentials, send_account_created_alert
from utils.url_generator import clean_domain, build_web_address, build_common_login_url
from models.department import Department
from models.designation import Designation
from models.branch import Branch
from models.payroll import PayGrade
from utils.audit_logger import log_action

admin_bp = Blueprint('admin', __name__)
@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN', 'EMPLOYEE'])
def get_employees():
    if g.user.role == 'SUPER_ADMIN':
        employees = Employee.query.all()
    elif g.user.role == 'EMPLOYEE':
        # Employee can only see their own record
        employees = Employee.query.filter_by(user_id=g.user.id).all()
    else:
        employees = Employee.query.filter_by(company_id=g.user.company_id).all()

    result = []
    for emp in employees:
        user = emp.user  # relationship
        company = Company.query.get(emp.company_id) if emp.company_id else None
        result.append({
            'id': emp.id,
            'employee_id': emp.employee_id,
            'user': (user.username if user and user.username else None) or
                    (emp.company_email.split('@')[0] if emp.company_email else (user.email.split('@')[0] if user else '')),
            'name': emp.full_name or '',
            'email': emp.company_email or (user.email if user else ''),
            'dept': emp.department or '',
            'desig': emp.designation or '',
            'type': user.role.capitalize() if user else 'Employee',
            'company': company.company_name if company else 'N/A',
            'company_id': emp.company_id,
            'phone': emp.phone_number or '',
            'status': user.status.capitalize() if user and user.status else 'Active',
        })
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/employees/<int:emp_id>', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN', 'EMPLOYEE'])
def get_employee(emp_id):
    if g.user.role == 'SUPER_ADMIN':
        emp = Employee.query.get(emp_id)
    elif g.user.role == 'EMPLOYEE':
        emp = Employee.query.filter_by(id=emp_id, user_id=g.user.id).first()
    else:
        emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    
    if not emp:
        return jsonify({'message': 'Employee not found or unauthorized'}), 404
        
    user = emp.user
    return jsonify({
        'success': True,
        'data': {
            'id': emp.id,
            'employee_id': emp.employee_id,
            'full_name': emp.full_name,
            'email': emp.company_email or (user.email if user else ''),
            'department': emp.department,
            'designation': emp.designation,
            'phone_number': emp.phone_number,
            'status': user.status if user else 'ACTIVE'
        }
    })

@admin_bp.route('/employees/<int:emp_id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'SUPER_ADMIN'])
def delete_employee(emp_id):
    """Permanently delete an employee and their user account from the database."""
    try:
        if g.user.role == 'SUPER_ADMIN':
            emp = Employee.query.get(emp_id)
        else:
            # ADMIN can only delete from their own company
            emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()

        if not emp:
            return jsonify({'success': False, 'message': 'Employee not found or unauthorized'}), 404

        emp_name = emp.full_name
        user_id = emp.user_id

        # Permanently delete the employee profile first (child record)
        db.session.delete(emp)
        db.session.flush()

        # Then permanently delete the user account (parent record)
        if user_id:
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)

        db.session.commit()
        log_action("DELETE_EMPLOYEE", "Employee", emp_id, 200, meta={"name": emp_name})
        return jsonify({'success': True, 'message': f'Employee "{emp_name}" permanently deleted.'}), 200

    except Exception as e:
        db.session.rollback()
        import traceback
        logging.error(f'delete_employee error: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'Delete failed: {str(e)}'}), 500

@admin_bp.route('/employees/<int:emp_id>', methods=['PUT', 'PATCH'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN'])
def update_employee(emp_id):
    if g.user.role == 'SUPER_ADMIN':
        emp = Employee.query.get(emp_id)
    else:
        emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
        
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404
        
    data = request.get_json(force=True) or {}
    # Update employee fields
    for field in ['full_name', 'department', 'designation', 'phone_number', 'personal_email']:
        if field in data:
            setattr(emp, field, data[field])
            
    if 'status' in data and emp.user:
        emp.user.status = data['status']
    
    db.session.commit()
    log_action("UPDATE_EMPLOYEE", "Employee", emp_id, 200, meta=data)
    return jsonify({'success': True, 'message': 'Employee updated successfully'})

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

@admin_bp.route('/dropdown-data', methods=['GET'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN', 'HR'])
def get_dropdown_data():
    company_id = g.user.company_id
    
    # If Super Admin, they might want all companies or a specific one? 
    # Usually dropdowns are context specific.
    
    departments = Department.query.filter_by(company_id=company_id).all()
    designations = Designation.query.filter_by(company_id=company_id).all()
    branches = Branch.query.filter_by(company_id=company_id).all()
    paygrades = PayGrade.query.filter_by(company_id=company_id, status='ACTIVE').all()
    
    # Managers: Users with MANAGER role in this company
    managers = Employee.query.join(User).filter(
        User.company_id == company_id,
        User.role == 'MANAGER'
    ).all()
    
    # Eligible Users: Users who don't have an employee profile yet
    eligible_users = User.query.filter(
        User.company_id == company_id,
        User.employee_profile == None
    ).all()

    return jsonify({
        "success": true,
        "data": {
            "departments": [{"id": d.id, "name": d.department_name} for d in departments],
            "designations": [{"id": d.id, "name": d.designation_name} for d in designations],
            "branches": [{"id": b.id, "name": b.branch_name} for b in branches],
            "paygrades": [{"id": p.id, "name": p.grade_name} for p in paygrades],
            "managers": [{"id": m.id, "name": m.full_name} for m in managers],
            "users": [{"id": u.id, "email": u.email} for u in eligible_users],
            "employment_types": ["Full-time", "Part-time", "Intern", "Contract", "Freelance"]
        }
    }), 200

def _parse_date(date_str):
    """Parse date flexibly from multiple formats."""
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%b %d, %Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    return None

def _resolve_branch_id(data, company_id):
    """Resolve branch_id from branch_id or branch_name."""
    branch_id = data.get('branch_id')
    if branch_id:
        return int(branch_id) if str(branch_id).isdigit() else None
    branch_name = data.get('branch_name')
    if branch_name:
        from models.branch import Branch
        branch = Branch.query.filter(
            Branch.branch_name.ilike(branch_name.strip()),
            Branch.company_id == company_id
        ).first()
        return branch.id if branch else None
    return None

@admin_bp.route('/create-manager', methods=['POST'])
@admin_bp.route('/create-employee', methods=['POST'])
@admin_bp.route('/create-hr', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN', 'ADMIN', 'HR'])
def create_employee():
    try:
        return _create_employee_impl()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        import logging
        logging.error(f'create_employee unhandled: {tb}')
        return jsonify({
            'success': False,
            'message': f'Server Error: {str(e)}',
            'detail': str(e),
            'trace': tb[-500:]
        }), 500

def _create_employee_impl():
    data = request.get_json(force=True) or {}
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    # 1. Validate Password
    password = data.get('password')
    if not password:
        return jsonify({'message': 'Password is required'}), 400

    # 2. Identify Company
    req_company_id = data.get('company_id')
    req_company_name = data.get('company_name')
    company = None

    if g.user.role == 'SUPER_ADMIN':
        if not req_company_id and not req_company_name:
            return jsonify({'message': 'company_id or company_name is required for Super Admin'}), 400

        if req_company_id:
            # Try by company_code first, then numeric ID
            company = Company.query.filter_by(company_code=req_company_id).first()
            if not company and str(req_company_id).isdigit():
                company = Company.query.get(int(req_company_id))

        if not company and req_company_name:
            # Lookup by exact or partial company name (case-insensitive)
            name_clean = req_company_name.strip()
            company = Company.query.filter(
                Company.company_name.ilike(name_clean)
            ).first()
            if not company:
                # Try contains match
                company = Company.query.filter(
                    Company.company_name.ilike(f'%{name_clean}%')
                ).first()

        if not company:
            return jsonify({'message': f'Company not found: {req_company_id or req_company_name}'}), 404
    else:
        # ADMIN can only create for their own company
        admin_company_id = g.user.company_id
        try:
            # Handle potential string/int mismatch
            cid_int = int(admin_company_id) if admin_company_id else None
            company = Company.query.get(cid_int)
        except (ValueError, TypeError):
            company = None

        if not company:
            return jsonify({'message': f'Admin company context not found (ID: {admin_company_id})'}), 404

    # 3. Check Email Uniqueness
    email = data.get('email') or data.get('company_email')
    personal_email = data.get('personal_email')
    
    if not email:
        return jsonify({'message': 'Email is required'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400

    # 4. Determine Role from employee_type or designation
    designation = data.get('designation', '').strip()
    employee_type = data.get('employee_type', '').strip().upper()
    username = data.get('username', '').strip() or email.split('@')[0]

    # Map type/designation to role
    role = 'EMPLOYEE'
    if employee_type in ['MANAGER', 'ADMIN', 'HR', 'SUPER_ADMIN']:
        role = employee_type
    else:
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
    # Set username if column exists
    try:
        new_user.username = username
    except Exception:
        pass
    try:
        db.session.add(new_user)
        db.session.flush()  # Generate ID
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'Email already registered or duplicate data', 'detail': str(e.orig)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating user account', 'detail': str(e)}), 500

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
        company_id=company.id,
        employee_id=data.get('employee_id') or new_emp_id,
        full_name=full_name,
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=_parse_date(data.get('date_of_joining')),
        gender=data.get('gender'),
        personal_email=data.get('personal_email'),
        pay_grade=data.get('pay_grade'),
        ctc=float(data.get('ctc', 0.0)),
        employment_type=data.get('employment_type'),
        branch_id=_resolve_branch_id(data, company.id),
        manager_id=data.get('manager_id'),
        phone_number=data.get('phone_number') or data.get('mobile_number'),
        company_email=email
    )
    
    # Save employee to DB first (guaranteed)
    try:
        db.session.add(new_employee)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating employee record", "error": str(e)}), 500

    # Try sending emails - don't fail the whole request if email fails
    email_sent = False
    try:
        created_by = "Super Admin" if g.user.role == 'SUPER_ADMIN' else "Admin"
        web_address = build_web_address(company.subdomain) if company.subdomain else "#"
        login_url = build_common_login_url(company.subdomain) if company.subdomain else "#"

        send_account_created_alert(personal_email or email, company.company_name, created_by)
        send_login_credentials(
            personal_email=personal_email or email,
            company_email=email,
            password=password,
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by=created_by
        )
        email_sent = True
    except Exception as email_err:
        # Log but don't fail - employee is already saved
        print(f"[WARNING] Email notification failed: {email_err}")

    log_action("CREATE_EMPLOYEE", "Employee", new_employee.id, 201, meta={"name": full_name, "role": role})

    return jsonify({
        'success': True,
        'message': f'{designation or role} created successfully',
        'employee_id': new_employee.employee_id,
        'company_email': email,
        'personal_email': personal_email,
        'email_sent': email_sent,
        'created_by': g.user.role
    }), 201