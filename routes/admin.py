from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash
from models import db
from models.user import User
from sqlalchemy import inspect, func
from sqlalchemy.exc import IntegrityError
from models.employee import Employee
from models.company import Company
from utils.decorators import token_required, role_required
from datetime import datetime, timedelta
import re
import logging
from utils.email_utils import send_login_credentials, send_account_created_alert
import jwt
from utils.url_generator import clean_domain, build_web_address, build_common_login_url
from models.department import Department
from models.designation import Designation
from models.branch import Branch
from models.payroll import PayGrade
from utils.audit_logger import log_action
from utils.date_utils import parse_date
from utils.decorators import token_required, role_required, permission_required
from constants.permissions_registry import Permissions

admin_bp = Blueprint('admin', __name__)
@admin_bp.route('/employees', methods=['GET'])
@token_required
@permission_required(Permissions.EMPLOYEE_VIEW)
def get_employees():
    # Default filter: only active
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    
    if g.user.role == 'SUPER_ADMIN':
        query = Employee.query
    elif g.user.role == 'EMPLOYEE':
        # Employee can only see their own record (regardless of status for now)
        query = Employee.query.filter_by(user_id=g.user.id)
    else:
        query = Employee.query.filter_by(company_id=g.user.company_id)

    if not include_inactive and g.user.role != 'EMPLOYEE':
        query = query.filter(Employee.is_active == True)
        
    employees = query.all()

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
            'department': emp.department or '',
            'designation': emp.designation or '',
            'role': user.role.capitalize() if user else 'Employee',
            'company': company.company_name if company else 'N/A',
            'company_id': emp.company_id,
            'phone': emp.phone_number or '',
            'status': user.status.capitalize() if user and user.status else 'Active',
            'joining_date': emp.date_of_joining.isoformat() if emp.date_of_joining else None,
            'pay_grade': emp.pay_grade or 'N/A'
        })
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/employees/<int:emp_id>', methods=['GET'])
@token_required
@permission_required(Permissions.EMPLOYEE_VIEW)
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
            'status': user.status if user else 'ACTIVE',
            'pay_grade': emp.pay_grade or 'N/A'
        }
    })

@admin_bp.route('/employees/<int:emp_id>', methods=['DELETE'])
@token_required
@permission_required(Permissions.EMPLOYEE_DELETE)
def deactivate_employee(emp_id):
    """Mark an employee and their user records as INACTIVE instead of deleting from the database."""
    try:
        if g.user.role == 'SUPER_ADMIN':
            emp = Employee.query.get(emp_id)
        else:
            # ADMIN can only deactivate from their own company
            emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()

        if not emp:
            return jsonify({'success': False, 'message': 'Employee not found or unauthorized'}), 404

        emp_name = emp.full_name
        user_id = emp.user_id

        # Mark Employee as INACTIVE
        emp.status = "INACTIVE"
        emp.is_active = False

        # Mark linked User as INACTIVE
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.status = "INACTIVE"
                user.is_active = False

        db.session.commit()
        log_action("DEACTIVATE_EMPLOYEE", "Employee", emp_id, 200, meta={"name": emp_name})
        return jsonify({'success': True, 'message': f'Employee "{emp_name}" has been deactivated successfully.'}), 200

    except Exception as e:
        db.session.rollback()
        import traceback
        logging.error(f'deactivate_employee error: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'Deactivation failed: {str(e)}'}), 500

@admin_bp.route('/employees/<int:emp_id>', methods=['PUT', 'PATCH'])
@token_required
@permission_required(Permissions.EMPLOYEE_EDIT)
def update_employee(emp_id):
    """Update an employee's profile and user account details."""
    if g.user.role == 'SUPER_ADMIN':
        emp = Employee.query.get(emp_id)
    else:
        emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
        
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404
        
    data = request.get_json(force=True) or {}
    
    # Update user account details if provided
    if emp.user:
        if 'company_email' in data:
            emp.user.email = data['company_email'].strip().lower()
        if 'username' in data:
            emp.user.username = data['username'].strip()
        if 'password' in data and data['password']:
            from werkzeug.security import generate_password_hash
            emp.user.password = generate_password_hash(data['password'])
            
        role_val = data.get('role') or data.get('user_role') or data.get('userRole')
        if role_val:
            emp.user.role = role_val.upper()
        
        # Synchronize Status and Active flags
        if 'status' in data:
            new_status = data['status'].upper()
            emp.user.status = new_status
            emp.status = new_status
            
            # If deactivating via update, set is_active flags
            if new_status == 'INACTIVE':
                emp.is_active = False
            elif new_status == 'ACTIVE':
                emp.is_active = True

    # Update employee fields
    direct_fields = ['full_name', 'department', 'designation', 'phone_number', 'personal_email', 'pay_grade', 'employment_type', 'gender', 'company_email']
    for field in direct_fields:
        camel_field = field.split('_')[0] + ''.join(x.title() for x in field.split('_')[1:])
        val = data.get(field)
        if val is None:
            val = data.get(camel_field)
            
        if val is not None:
            setattr(emp, field, val)
            
    # Complex fields
    if 'date_of_joining' in data or 'joining_date' in data:
        emp.date_of_joining = parse_date(data.get('date_of_joining') or data.get('joining_date'))
        
    if 'branch_id' in data:
        emp.branch_id = _resolve_branch_id(data, emp.company_id)
        
    if 'manager_id' in data:
        emp.manager_id = data['manager_id']

    # Explicitly ignore CTC
    if 'ctc' in data:
        pass
    
    try:
        db.session.commit()
        log_action("UPDATE_EMPLOYEE", "Employee", emp_id, 200, meta=data)
        return jsonify({'success': True, 'message': 'Employee updated successfully'})
    except Exception as e:
        db.session.rollback()
        logging.error(f'update_employee error: {str(e)}')
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 500

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
@permission_required(Permissions.EMPLOYEE_VIEW)
def get_dropdown_data():
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', type=int)
    
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
        "success": True,
        "data": {
            "departments": [{"id": d.id, "name": d.department_name} for d in departments],
            "designations": [{"id": d.id, "name": d.designation_name} for d in designations],
            "branches": [{"id": b.id, "name": b.branch_name} for b in branches],
            "paygrades": [{"id": p.id, "name": p.grade_name} for p in paygrades],
            "managers": [{"id": m.id, "name": m.full_name} for m in managers],
            "users": [{"id": u.id, "email": u.email} for u in eligible_users],
            "employment_types": ["Full-time", "Part-time", "Intern", "Contract", "Freelance"],
            "companies": [{"id": c.id, "name": c.company_name} for c in Company.query.all()] if g.user.role == 'SUPER_ADMIN' else []
        }
    }), 200

# __parse_date_util removed to use central parse_date

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
@permission_required(Permissions.EMPLOYEE_CREATE)
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

    # 4. Determine Role from employee_type, role, or designation
    designation = data.get('designation', '').strip()
    employee_type = (data.get('employee_type') or data.get('role') or '').strip().upper()
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
    full_name = (data.get("full_name") or data.get("name") or "").strip()
    if not full_name:
        return jsonify({"success": False, "message": "full_name or name is required"}), 400

    new_employee = Employee(
        user_id=new_user.id,
        company_id=company.id,
        employee_id=data.get('employee_id') or new_emp_id,
        full_name=full_name,
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=parse_date(data.get('date_of_joining') or data.get('joining_date')),
        gender=data.get('gender'),
        personal_email=data.get('personal_email'),
        pay_grade=data.get('pay_grade') or 'N/A',
        employment_type=data.get('employment_type'),
        branch_id=_resolve_branch_id(data, company.id),
        manager_id=data.get('manager_id'),
        phone_number=data.get('phone_number') or data.get('mobile_number') or data.get('phone'),
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
        # Generate a reset token for the email link
        reset_token = jwt.encode(
            {
                'user_id': new_employee.id,
                'type': 'password_reset',
                'exp': datetime.utcnow() + timedelta(minutes=60)
            },
            current_app.config['SECRET_KEY'],
            algorithm="HS256"
        )
        # Generate OTP as a fallback
        otp = new_employee.generate_otp()
        reset_url = f"{login_url.replace('/login', '/reset-password')}?token={reset_token}&email={email or personal_email}&otp={otp}"

        send_login_credentials(
            personal_email=personal_email or email,
            company_email=email,
            company_name=company.company_name,
            web_address=web_address,
            reset_url=reset_url,
            created_by=created_by,
            full_name=data.get("full_name") or data.get("name") or "User"
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

@admin_bp.route("/employees/<int:emp_id>/toggle", methods=["POST"])
@admin_bp.route("/employees/<int:emp_id>/toggle status", methods=["POST"])
@admin_bp.route("/employees/<int:emp_id>/toggle-status", methods=["POST"])
@token_required
@permission_required(Permissions.EMPLOYEE_STATUS_TOGGLE)
def toggle_employee_status_admin(emp_id):
    """
    Hierarchical Status Toggle:
    - ADMIN can toggle anyone in their company except SUPER_ADMIN.
    - HR can toggle only MANAGER and EMPLOYEE in their company.
    """
    emp = Employee.query.get_or_404(emp_id)
    target_user = User.query.get(emp.user_id) if emp.user_id else None
    
    if not target_user:
        return jsonify({"success": False, "message": "Linked user account not found"}), 404

    # 1. Company Check (Admin/HR must be in same company)
    if g.user.role != 'SUPER_ADMIN' and target_user.company_id != g.user.company_id:
        return jsonify({"success": False, "message": "Unauthorized: Employee belongs to a different company"}), 403

    # 2. Hierarchy Check
    current_role = (g.user.role or "").upper()
    target_role = (target_user.role or "").upper()
    
    # Hierarchy Rules
    if current_role == 'ADMIN':
        if target_role == 'SUPER_ADMIN':
            return jsonify({"success": False, "message": "Forbidden: Admin cannot toggle Super Admin status"}), 403
            
    elif current_role == 'HR':
        if target_role not in ['MANAGER', 'EMPLOYEE']:
            return jsonify({"success": False, "message": f"Forbidden: HR cannot toggle {target_role} status"}), 403
            
    elif current_role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
         return jsonify({"success": False, "message": "Forbidden: Insufficient permissions"}), 403

    # 3. Perform Toggle
    current_status = (target_user.status or "ACTIVE").upper()
    new_status = "INACTIVE" if current_status == "ACTIVE" else "ACTIVE"

    target_user.status = new_status
    # Synchronize is_active flag (handled by property in User model)
    
    emp.status = new_status
    emp.is_active = (new_status == "ACTIVE")

    db.session.commit()
    
    log_action("TOGGLE_STATUS", "Employee", emp.id, 200, 
               meta={"name": emp.full_name, "old": current_status, "new": new_status, "by": current_role})

    return jsonify({
        "success": True,
        "message": f"Status for {emp.full_name} changed to {new_status}",
        "new_status": new_status
    }), 200