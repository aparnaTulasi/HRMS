import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created/Updated: {path}")

# ---------------------------------------------------------
# 1. ROUTE FILES (To be placed in routes/)
# ---------------------------------------------------------

routes_init = ""

routes_auth = """from flask import Blueprint, request, jsonify
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

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user: return jsonify({'message': 'User not found'}), 404
    if user.status != 'PENDING_OTP': return jsonify({'message': 'Invalid status'}), 400
    if len(data['otp']) != 6 or not data['otp'].isdigit(): return jsonify({'message': 'Invalid OTP'}), 400
    user.status = 'PENDING'
    user.otp = None
    user.otp_expiry = None
    db.session.commit()
    return jsonify({'message': 'OTP verified. Waiting for admin approval.', 'status': 'PENDING', 'email': user.email}), 200

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if 'email' not in data or 'password' not in data: return jsonify({'message': 'Email and password required'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']): return jsonify({'message': 'Invalid credentials'}), 401
    if user.status == 'PENDING_OTP': return jsonify({'message': 'Verify OTP first', 'status': 'PENDING_OTP', 'email': user.email}), 403
    if user.role == 'EMPLOYEE' and user.status == 'PENDING': return jsonify({'message': 'Waiting for admin approval', 'status': 'PENDING'}), 403
    if user.status != 'ACTIVE': return jsonify({'message': 'Account not active'}), 403
    
    token = jwt.encode({
        'user_id': user.id, 'email': user.email, 'role': user.role,
        'company_id': user.company_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")
    return jsonify({'token': token, 'role': user.role, 'status': user.status, 'user_id': user.id, 'email': user.email, 'message': 'Login successful'})

@auth_bp.route('/check-status', methods=['GET'])
def check_status():
    email = request.args.get('email')
    if not email: return jsonify({'message': 'Email required'}), 400
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({'message': 'User not found'}), 404
    return jsonify({'email': user.email, 'status': user.status, 'role': user.role, 'message': f'Status: {user.status}'})
"""

routes_admin = """from flask import Blueprint, jsonify, request, g
from models import db
from models.user import User
from models.employee import Employee
from models.company import Company
from utils.decorators import token_required, role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    output = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        output.append({'id': emp.id, 'user_id': emp.user_id, 'first_name': emp.first_name, 'last_name': emp.last_name, 'email': user.email, 'status': user.status, 'department': emp.department, 'designation': emp.designation})
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
            output.append({'user_id': user.id, 'first_name': emp.first_name, 'last_name': emp.last_name, 'email': user.email, 'department': emp.department, 'designation': emp.designation, 'date_of_joining': emp.date_of_joining})
    return jsonify({'pending_employees': output})

@admin_bp.route('/approve-employee/<int:user_id>', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def approve_employee(user_id):
    user = User.query.get(user_id)
    if not user: return jsonify({'message': 'User not found'}), 404
    if user.company_id != g.user.company_id: return jsonify({'message': 'Unauthorized access'}), 403
    user.status = 'ACTIVE'
    db.session.commit()
    return jsonify({'message': 'Employee approved successfully', 'status': 'ACTIVE'})
"""

routes_superadmin = """from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
import random
from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required
from utils.url_generator import clean_username

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json()
    if Company.query.filter_by(subdomain=data['subdomain']).first(): return jsonify({'message': 'Subdomain already exists'}), 409
    if User.query.filter_by(email=data['admin_email']).first(): return jsonify({'message': 'Admin email already exists'}), 409
    
    new_company = Company(company_name=data['company_name'], subdomain=data['subdomain'])
    db.session.add(new_company)
    db.session.flush()
    
    hashed_password = generate_password_hash(data['admin_password'], method='pbkdf2:sha256')
    new_admin = User(email=data['admin_email'], password=hashed_password, role='ADMIN', company_id=new_company.id, status='ACTIVE', portal_prefix='aparna')
    db.session.add(new_admin)
    db.session.flush()
    
    admin_emp = Employee(user_id=new_admin.id, company_id=new_company.id, first_name=data.get('admin_first_name', 'Admin'), last_name=data.get('admin_last_name', 'User'), department='Management', designation='Administrator')
    db.session.add(admin_emp)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Company created successfully', 'company': {'id': new_company.id, 'name': new_company.company_name, 'subdomain': new_company.subdomain}, 'admin': {'email': data['admin_email']}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating company', 'error': str(e)}), 500

@superadmin_bp.route('/companies', methods=['GET'])
@token_required
@role_required(['SUPER_ADMIN'])
def get_companies():
    companies = Company.query.all()
    output = []
    for company in companies:
        admin = User.query.filter_by(company_id=company.id, role='ADMIN').first()
        employee_count = Employee.query.filter_by(company_id=company.id).count()
        output.append({'id': company.id, 'company_name': company.company_name, 'subdomain': company.subdomain, 'created_at': company.created_at.strftime('%Y-%m-%d %H:%M'), 'admin_email': admin.email if admin else 'No admin', 'employee_count': employee_count})
    return jsonify({'companies': output, 'count': len(output)})
"""

routes_hr = """from flask import Blueprint, jsonify, request, g
from models import db
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required

hr_bp = Blueprint('hr', __name__)

@hr_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    output = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        output.append({'id': emp.id, 'first_name': emp.first_name, 'last_name': emp.last_name, 'email': user.email, 'status': user.status, 'department': emp.department, 'designation': emp.designation})
    return jsonify({'employees': output})

@hr_bp.route('/approve-employee/<int:user_id>', methods=['POST'])
@token_required
@role_required(['HR'])
def approve_employee(user_id):
    user = User.query.get(user_id)
    if not user: return jsonify({'message': 'User not found'}), 404
    if user.company_id != g.user.company_id: return jsonify({'message': 'Unauthorized access'}), 403
    user.status = 'ACTIVE'
    db.session.commit()
    return jsonify({'message': 'Employee approved successfully', 'status': 'ACTIVE'})
"""

routes_employee = """from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocuments
from models.user import User
from utils.decorators import token_required

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/check-registration', methods=['GET'])
def check_registration():
    email = request.args.get('email')
    if not email: return jsonify({'message': 'Email required'}), 400
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({'message': 'No registration found'}), 404
    emp = Employee.query.filter_by(user_id=user.id).first()
    return jsonify({'email': user.email, 'status': user.status, 'name': f"{emp.first_name} {emp.last_name}" if emp else None, 'role': user.role})

@employee_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Profile not found'}), 404
    return jsonify({'id': emp.id, 'first_name': emp.first_name, 'last_name': emp.last_name, 'department': emp.department, 'designation': emp.designation, 'phone': emp.phone, 'date_of_joining': emp.date_of_joining})

@employee_bp.route('/bank', methods=['GET'])
@token_required
def get_bank():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({})
    bank = EmployeeBankDetails.query.filter_by(employee_id=emp.id).first()
    if not bank: return jsonify({})
    return jsonify({'bank_name': bank.bank_name, 'account_number': bank.account_number, 'ifsc_code': bank.ifsc_code})

@employee_bp.route('/bank', methods=['POST'])
@token_required
def add_bank():
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    bank = EmployeeBankDetails.query.filter_by(employee_id=emp.id).first()
    if not bank:
        bank = EmployeeBankDetails(employee_id=emp.id)
        db.session.add(bank)
    bank.bank_name = data.get('bank_name')
    bank.account_number = data.get('account_number')
    bank.ifsc_code = data.get('ifsc_code')
    db.session.commit()
    return jsonify({'message': 'Bank details updated successfully'})
"""

routes_attendance = """from flask import Blueprint, jsonify, request, g
from datetime import datetime, date
from models import db
from models.attendance import Attendance
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, role_required, permission_required

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/mark-in', methods=['POST'])
@token_required
def mark_in_time():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    today = date.today()
    existing = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    if existing and existing.in_time: return jsonify({'message': 'Already marked in for today'}), 400
    
    if existing:
        existing.in_time = datetime.utcnow()
        existing.status = 'PRESENT'
        existing.marked_by = 'SELF'
    else:
        attendance = Attendance(employee_id=emp.id, date=today, in_time=datetime.utcnow(), status='PRESENT', year=today.year, month=today.month, marked_by='SELF')
        db.session.add(attendance)
    db.session.commit()
    return jsonify({'message': 'In time marked successfully', 'in_time': datetime.utcnow().strftime('%H:%M:%S'), 'date': today.strftime('%Y-%m-%d')})

@attendance_bp.route('/mark-out', methods=['POST'])
@token_required
def mark_out_time():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    if not attendance: return jsonify({'message': 'In time not marked yet'}), 400
    if attendance.out_time: return jsonify({'message': 'Already marked out for today'}), 400
    attendance.out_time = datetime.utcnow()
    if attendance.in_time:
        work_seconds = (attendance.out_time - attendance.in_time).total_seconds()
        attendance.work_hours = round(work_seconds / 3600, 2)
    db.session.commit()
    return jsonify({'message': 'Out time marked successfully', 'out_time': datetime.utcnow().strftime('%H:%M:%S'), 'work_hours': attendance.work_hours})

@attendance_bp.route('/my-attendance', methods=['GET'])
@token_required
def get_my_attendance():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    month = request.args.get('month', datetime.utcnow().month, type=int)
    year = request.args.get('year', datetime.utcnow().year, type=int)
    attendance = Attendance.query.filter_by(employee_id=emp.id, year=year, month=month).all()
    output = [{'date': r.date.strftime('%Y-%m-%d'), 'in_time': r.in_time.strftime('%H:%M:%S') if r.in_time else None, 'out_time': r.out_time.strftime('%H:%M:%S') if r.out_time else None, 'status': r.status, 'work_hours': r.work_hours} for r in attendance]
    return jsonify({'attendance': output})
"""

routes_employee_advanced = """from flask import Blueprint, jsonify, request, g
from datetime import datetime, date
from sqlalchemy import or_, and_
import json
from models import db
from models.employee import Employee
from models.user import User
from models.department import Department
from models.filter import FilterConfiguration
from utils.decorators import token_required, role_required, permission_required

employee_advanced_bp = Blueprint('employee_advanced', __name__)

@employee_advanced_bp.route('/filter', methods=['POST'])
@token_required
def filter_employees():
    if g.user.role == 'EMPLOYEE':
        emp = Employee.query.filter_by(user_id=g.user.id).first()
        return jsonify({'employees': [{'id': emp.id, 'first_name': emp.first_name, 'last_name': emp.last_name, 'email': g.user.email, 'department': emp.department, 'designation': emp.designation, 'status': emp.employee_status}], 'count': 1})
    
    data = request.get_json()
    filters = data.get('filters', {})
    query = Employee.query.filter_by(company_id=g.user.company_id)
    
    if 'department' in filters and filters['department'] != 'All': query = query.filter_by(department=filters['department'])
    if 'designation' in filters: query = query.filter_by(designation=filters['designation'])
    if 'status' in filters: query = query.filter_by(employee_status=filters['status'])
    
    employees = query.all()
    output = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        output.append({'id': emp.id, 'first_name': emp.first_name, 'last_name': emp.last_name, 'email': user.email if user else None, 'department': emp.department, 'designation': emp.designation, 'status': emp.employee_status})
    return jsonify({'employees': output, 'count': len(output)})

@employee_advanced_bp.route('/departments', methods=['GET'])
@token_required
def get_departments():
    if g.user.role == 'EMPLOYEE':
        emp = Employee.query.filter_by(user_id=g.user.id).first()
        return jsonify({'departments': [emp.department] if emp.department else []})
    departments = db.session.query(Employee.department).filter_by(company_id=g.user.company_id).distinct().all()
    return jsonify({'departments': ['All'] + sorted([d[0] for d in departments if d[0]])})
"""

routes_urls = """from flask import Blueprint, jsonify, request, g
import json
from models import db
from models.urls import SystemURL
from utils.decorators import token_required, role_required

urls_bp = Blueprint('urls', __name__)

@urls_bp.route('/add', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def add_url():
    data = request.get_json()
    url = SystemURL(url_code=data['url_code'], url_path=data['url_path'], description=data.get('description'), module=data.get('module'), allowed_roles=json.dumps(data.get('allowed_roles', [])), permission_required=data.get('permission_required'), is_active=data.get('is_active', True), is_public=data.get('is_public', False), company_id=data.get('company_id'))
    db.session.add(url)
    db.session.commit()
    return jsonify({'message': 'URL added successfully', 'url_id': url.id})

@urls_bp.route('/list', methods=['GET'])
@token_required
def list_urls():
    urls = SystemURL.query.filter_by(is_active=True).all()
    output = []
    for url in urls:
        try: allowed_roles = json.loads(url.allowed_roles)
        except: allowed_roles = []
        has_access = (url.is_public or g.user.role in allowed_roles or g.user.role == 'SUPER_ADMIN' or (url.company_id and url.company_id == g.user.company_id))
        if has_access: output.append({'url_code': url.url_code, 'url_path': url.url_path, 'description': url.description})
    return jsonify({'urls': output})
"""

routes_permissions = """from flask import Blueprint, jsonify, request, g
import json
from models import db
from models.permission import Permission, UserPermission
from models.user import User
from utils.decorators import token_required, role_required

permissions_bp = Blueprint('permissions', __name__)

@permissions_bp.route('/assign', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def assign_permission():
    data = request.get_json()
    user = User.query.get(data['user_id'])
    if not user: return jsonify({'message': 'User not found'}), 404
    UserPermission.query.filter_by(user_id=user.id, permission_code=data['permission_code']).delete()
    user_perm = UserPermission(user_id=user.id, permission_code=data['permission_code'], granted_by=g.user.id)
    db.session.add(user_perm)
    db.session.commit()
    return jsonify({'message': 'Permission assigned successfully'})
"""

# ---------------------------------------------------------
# 2. MODEL FILES (Restoring correct models)
# ---------------------------------------------------------

models_attendance = """from datetime import datetime
from models import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ABSENT')
    work_hours = db.Column(db.Float, default=0.0)
    year = db.Column(db.Integer, default=datetime.utcnow().year)
    month = db.Column(db.Integer, default=datetime.utcnow().month)
    marked_by = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_attendance'),)
"""

models_urls = """from datetime import datetime
from models import db

class SystemURL(db.Model):
    __tablename__ = 'system_urls'
    id = db.Column(db.Integer, primary_key=True)
    url_code = db.Column(db.String(50), unique=True, nullable=False)
    url_path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    module = db.Column(db.String(50))
    allowed_roles = db.Column(db.Text)
    permission_required = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company = db.relationship('Company', backref='urls')
"""

leave_init = """from flask import Blueprint

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

from . import routes
"""

leave_models = """from datetime import datetime
from models import db

class LeaveType(db.Model):
    __tablename__ = 'leave_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    max_days = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    
    leaves = db.relationship('Leave', backref='leave_type', lazy=True)

class Leave(db.Model):
    __tablename__ = 'leaves'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected, cancelled
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    approved_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    approver = db.relationship('Employee', foreign_keys=[approved_by])

class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_allotted = db.Column(db.Integer, default=0)
    used = db.Column(db.Integer, default=0)
    remaining = db.Column(db.Integer, default=0)
    carried_over = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('employee_id', 'leave_type_id', 'year'),)
    
    employee = db.relationship('Employee', backref='leave_balances')
    leave_type = db.relationship('LeaveType', backref='balances')
"""

leave_routes = """from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from . import leave_bp
from .models import Leave, LeaveType, LeaveBalance
from models import db

@leave_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if request.method == 'POST':
        # Add leave application logic
        pass
    return render_template('leave/apply_leave.html')

@leave_bp.route('/history')
@login_required
def leave_history():
    leaves = Leave.query.filter_by(employee_id=current_user.id).all()
    return render_template('leave/leave_history.html', leaves=leaves)

@leave_bp.route('/balance')
@login_required
def leave_balance():
    balances = LeaveBalance.query.filter_by(employee_id=current_user.id).all()
    return render_template('leave/leave_balance.html', balances=balances)

@leave_bp.route('/manage')
@login_required
def manage_leave():
    # For managers to approve/reject leaves
    pending_leaves = Leave.query.filter_by(status='pending').all()
    return render_template('leave/manage_leave.html', leaves=pending_leaves)

@leave_bp.route('/api/leave-types')
@login_required
def get_leave_types():
    types = LeaveType.query.filter_by(is_active=True).all()
    return jsonify([{'id': t.id, 'name': t.name} for t in types])
"""

def fix_structure():
    print("🔧 Fixing Project Structure...")
    
    # 1. Create routes/ directory and files
    create_file('routes/__init__.py', routes_init)
    create_file('routes/auth.py', routes_auth)
    create_file('routes/admin.py', routes_admin)
    create_file('routes/superadmin.py', routes_superadmin)
    create_file('routes/hr.py', routes_hr)
    create_file('routes/employee.py', routes_employee)
    create_file('routes/attendance.py', routes_attendance)
    create_file('routes/employee_advanced.py', routes_employee_advanced)
    create_file('routes/urls.py', routes_urls)
    create_file('routes/permissions.py', routes_permissions)
    
    # 2. Restore Model files (overwriting misplaced route code)
    create_file('models/attendance.py', models_attendance)
    create_file('models/urls.py', models_urls)
    
    # 3. Create Leave Module files
    create_file('leave/__init__.py', leave_init)
    create_file('leave/models.py', leave_models)
    create_file('leave/routes.py', leave_routes)
    
    print("\n✨ Project structure fixed! You can now run 'python app.py'")

if __name__ == '__main__':
    fix_structure()