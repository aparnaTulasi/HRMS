import os
import shutil

def create_file(path, content):
    """Helper function to create a file with content."""
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"✅ Created/Updated: {path}")

def delete_path(path):
    """Helper function to delete a file or directory."""
    if not os.path.exists(path):
        return
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            print(f"🗑️  Deleted directory: {path}")
        else:
            os.remove(path)
            print(f"🗑️  Deleted file: {path}")
    except Exception as e:
        print(f"❌ Error deleting {path}: {e}")

# ==============================================================================
# CORRECT FILE CONTENTS
# ==============================================================================

app_py_content = """
from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from config import Config
from models import db

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'message': 'Authentication required'}), 401

# Import blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.superadmin import superadmin_bp
from routes.hr import hr_bp
from routes.attendance import attendance_bp
from routes.employee_advanced import employee_advanced_bp
from routes.urls import urls_bp
from routes.permissions import permissions_bp
from routes.documents import documents_bp
from leave.routes import leave_bp
 from routes.payroll import payroll_bp
from routes.profile_routes import profile_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
app.register_blueprint(hr_bp, url_prefix='/api/hr')
app.register_blueprint(employee_bp, url_prefix='/api/employee')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(employee_advanced_bp, url_prefix='/api/employee')
app.register_blueprint(urls_bp, url_prefix='/api/urls')
app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(leave_bp)
app.register_blueprint(payroll_bp, url_prefix='/api/payroll')
app.register_blueprint(profile_bp)

@app.route('/')
def home():
    return jsonify({'message': 'HRMS API Running', 'version': '2.0'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("✅ HRMS Server Starting...")
    app.run(debug=True, port=5000)
"""

config_py_content = """
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

class Config:
    SECRET_KEY = "hrms-secret-key-change-this"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_DIR, 'hrms.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    BASE_URL = "http://localhost:5000"

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
"""

models_init_py_content = "from flask_sqlalchemy import SQLAlchemy\ndb = SQLAlchemy()"

models_user_py_content = """
from datetime import datetime, timedelta
from flask_login import UserMixin
from models import db
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')
    portal_prefix = db.Column(db.String(50), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee_profile = db.relationship('Employee', backref='user', uselist=False, lazy=True)
    permissions = db.relationship('UserPermission', backref='user', lazy=True)

    def generate_otp(self):
        if self.role == 'EMPLOYEE':
            self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
            self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            return self.otp
        return None

    def has_permission(self, permission_code):
        if self.role == 'SUPER_ADMIN':
            return True
        return any(p.permission_code == permission_code for p in self.permissions)
"""

models_company_py_content = """
from datetime import datetime
from models import db

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    company_code = db.Column(db.String(20), unique=True)
    industry = db.Column(db.String(100))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    attendance_enabled = db.Column(db.Boolean, default=True)
    leave_enabled = db.Column(db.Boolean, default=True)
    payroll_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    users = db.relationship('User', backref='company', lazy=True)
    employees = db.relationship('Employee', backref='company', lazy=True)
    departments = db.relationship('Department', backref='company', lazy=True)
"""

models_employee_py_content = """
from datetime import datetime
from models import db

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    department = db.Column(db.String(50))
    designation = db.Column(db.String(50))
    date_of_joining = db.Column(db.Date)
    work_phone = db.Column(db.String(20))
    personal_mobile = db.Column(db.String(20))
    personal_email = db.Column(db.String(120))
    aadhaar_number = db.Column(db.String(20), unique=True)
    pan_number = db.Column(db.String(20), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bank_details = db.relationship('EmployeeBankDetails', backref='employee', uselist=False, lazy=True)
    address = db.relationship('EmployeeAddress', backref='employee', uselist=False, lazy=True)
    documents = db.relationship('EmployeeDocument', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
"""

models_attendance_py_content = """
from datetime import datetime
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

models_permission_py_content = """
from datetime import datetime
from models import db

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    permission_code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    module = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserPermission(db.Model):
    __tablename__ = 'user_permissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    permission_code = db.Column(db.String(50), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
"""

models_department_py_content = """
from datetime import datetime
from models import db

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    department_code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    manager = db.relationship('Employee', foreign_keys=[manager_id])
"""

models_filter_py_content = """
from datetime import datetime
from models import db
import json

class FilterConfiguration(db.Model):
    __tablename__ = 'filter_configurations'
    id = db.Column(db.Integer, primary_key=True)
    filter_name = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    filter_config = db.Column(db.Text)
    allowed_roles = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
"""

models_urls_py_content = """
from datetime import datetime
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

models_employee_address_py_content = """
from models import db

class EmployeeAddress(db.Model):
    __tablename__ = 'employee_address'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), unique=True, nullable=False)
    address_line1 = db.Column(db.String(200))
    permanent_address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
"""

models_employee_bank_py_content = """
from models import db

class EmployeeBankDetails(db.Model):
    __tablename__ = 'employee_bank_details'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), unique=True, nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    branch_name= db.Column(db.String(100),nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    ifsc_code = db.Column(db.String(20), nullable=False)
"""

models_employee_documents_py_content = """
from datetime import datetime
from models import db

class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)
    document_number = db.Column(db.String(100))
    document_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_url = db.Column(db.String(500))
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentType(db.Model):
    __tablename__ = 'document_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=False)
    requires_expiry_date = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
"""

routes_auth_py_content = """
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import secrets
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
        return jsonify({'message': 'User already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(email=data['email'], password=hashed_password, role=data.get('role', 'EMPLOYEE'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user_id': user.id, 'email': user.email, 'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")
    return jsonify({'token': token})
"""

routes_admin_py_content = """
from flask import Blueprint, jsonify, g
from utils.decorators import token_required, role_required
from models.employee import Employee

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([{'id': emp.id, 'name': emp.full_name} for emp in employees])
"""

routes_superadmin_py_content = """
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json()
    new_company = Company(company_name=data['company_name'], subdomain=data['subdomain'])
    db.session.add(new_company)
    db.session.flush()

    hashed_password = generate_password_hash(data['admin_password'], method='pbkdf2:sha256')
    new_admin = User(email=data['admin_email'], password=hashed_password, role='ADMIN', company_id=new_company.id)
    db.session.add(new_admin)
    db.session.flush()

    admin_emp = Employee(user_id=new_admin.id, company_id=new_company.id, first_name=data.get('admin_first_name', 'Admin'), last_name=data.get('admin_last_name', 'User'))
    db.session.add(admin_emp)
    db.session.commit()
    return jsonify({'message': 'Company and Admin created'}), 201
"""

routes_hr_py_content = """
from flask import Blueprint, jsonify, request, g
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
        output.append({
            'id': emp.id,
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'email': user.email,
            'status': user.status,
            'department': emp.department,
            'designation': emp.designation
        })
    return jsonify({'employees': output})

@hr_bp.route('/approve-employee/<int:user_id>', methods=['POST'])
@token_required
@role_required(['HR'])
def approve_employee(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    if user.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized access'}), 403
    user.status = 'ACTIVE'
    db.session.commit()
    return jsonify({'message': 'Employee approved successfully', 'status': 'ACTIVE'})
"""

routes_employee_py_content = """
from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocument
from utils.decorators import token_required
import os
from config import Config
from werkzeug.utils import secure_filename

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Profile not found'}), 404
    return jsonify({
        'id': emp.id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'department': emp.department,
        'designation': emp.designation,
        'phone': getattr(emp, 'work_phone', None),
        'date_of_joining': emp.date_of_joining.isoformat() if emp.date_of_joining else None
    })

# Other employee routes like /bank, /address etc. would go here
"""

routes_attendance_py_content = """
from flask import Blueprint, jsonify, request, g
from datetime import datetime, date
from models import db
from models.attendance import Attendance
from models.employee import Employee
from utils.decorators import token_required

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
    else:
        attendance = Attendance(employee_id=emp.id, date=today, in_time=datetime.utcnow(), status='PRESENT')
        db.session.add(attendance)
    db.session.commit()
    return jsonify({'message': 'In time marked successfully'})
"""

routes_employee_advanced_py_content = "from flask import Blueprint\nemployee_advanced_bp = Blueprint('employee_advanced', __name__)"
routes_urls_py_content = "from flask import Blueprint\nurls_bp = Blueprint('urls', __name__)"
routes_permissions_py_content = "from flask import Blueprint\npermissions_bp = Blueprint('permissions', __name__)"

routes_documents_py_content = """
import os
from flask import Blueprint, request, jsonify, send_file, current_app, g
from werkzeug.utils import secure_filename
from models import db
from models.employee_documents import EmployeeDocument, DocumentType
from models.employee import Employee
from utils.decorators import token_required
import uuid
from datetime import datetime

documents_bp = Blueprint('documents', __name__)

def get_upload_folder():
    upload_folder = os.path.join(current_app.root_path, 'uploads', 'documents')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

@documents_bp.route('/upload', methods=['POST'])
@token_required
def upload_document():
    if 'document_file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['document_file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    upload_folder = get_upload_folder()
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    new_document = EmployeeDocument(
        employee_id=g.user.employee_profile.id,
        document_type=request.form.get('document_type'),
        document_name=original_filename,
        file_path=file_path,
        file_url=f"/api/documents/download/{unique_filename}"
    )
    db.session.add(new_document)
    db.session.commit()
    return jsonify({'message': 'Document uploaded successfully'}), 201

@documents_bp.route('/download/<filename>')
@token_required
def download_document(filename):
    document = EmployeeDocument.query.filter(EmployeeDocument.file_url.endswith(filename)).first_or_404()
    if document.employee_id != g.user.employee_profile.id and g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
        return jsonify({'message': 'Access denied'}), 403
    return send_file(document.file_path, as_attachment=True)
"""

leave_init_py_content = "from flask import Blueprint\nleave_bp = Blueprint('leave', __name__, url_prefix='/leave')\nfrom . import routes"

leave_models_py_content = """
from datetime import datetime
from models import db

class LeaveType(db.Model):
    __tablename__ = 'leave_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    leaves = db.relationship('Leave', backref='leave_type', lazy=True)

class Leave(db.Model):
    __tablename__ = 'leaves'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employee = db.relationship('Employee', foreign_keys=[employee_id])

class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_allotted = db.Column(db.Integer, default=0)
    used = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint('employee_id', 'leave_type_id', 'year'),)
    employee = db.relationship('Employee', backref='leave_balances')
    leave_type = db.relationship('LeaveType', backref='balances')
"""

leave_routes_py_content = """
from flask import request, jsonify, g
from utils.decorators import token_required, role_required
from . import leave_bp
from .models import Leave
from models import db
from models.employee import Employee
from datetime import datetime

@leave_bp.route('/apply', methods=['POST'])
@token_required
def apply_leave():
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404

    new_leave = Leave(
        employee_id=emp.id,
        leave_type_id=data['leave_type_id'],
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
        reason=data['reason']
    )
    db.session.add(new_leave)
    db.session.commit()
    return jsonify({'message': 'Leave application submitted'}), 201

@leave_bp.route('/<int:id>/approve', methods=['POST'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def approve_leave(id):
    leave = Leave.query.get_or_404(id)
    
    approver_emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not approver_emp:
        return jsonify({'message': 'Approver profile not found'}), 404

    if leave.employee_id == approver_emp.id:
        return jsonify({'message': 'Cannot approve your own leave'}), 403
        
    data = request.get_json()
    leave.status = data.get('status', 'APPROVED')
    db.session.commit()
    return jsonify({'message': f'Leave {leave.status.lower()}'})
"""

utils_decorators_py_content = """
from flask import request, jsonify, g
import jwt
from functools import wraps
from config import Config
from models.user import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            g.user = User.query.get(data['user_id'])
            if not g.user:
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user.role not in allowed_roles:
                return jsonify({'message': 'Permission denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user.has_permission(permission_code):
                return jsonify({'message': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
"""

utils_url_generator_py_content = """
import re

def clean_username(email):
    if not email or '@' not in email:
        return "user"
    username = email.split('@')[0].lower()
    return re.sub(r'[^a-zA-Z0-9]', '', username)

def generate_login_url(email, role, company=None):
    username = clean_username(email)
    if role == 'SUPER_ADMIN':
        return f"https://{username}.superadmin.hrms.com"
    if company:
        return f"https://{company.subdomain}.hrms.com/{username}"
    return f"https://hrms.com/{username}"
"""

# ==============================================================================
# MAIN ORGANIZATION LOGIC
# ==============================================================================

def organize_project():
    """
    Cleans up the project directory by creating a standard structure,
    writing the correct code to files, and deleting obsolete/misplaced files.
    """
    print("🚀 Starting project organization...")

    # 1. Define the desired file structure and content
    project_files = {
        "app.py": app_py_content,
        "config.py": config_py_content,
        "routes/__init__.py": "",
        "routes/auth.py": routes_auth_py_content,
        "routes/admin.py": routes_admin_py_content,
        "routes/superadmin.py": routes_superadmin_py_content,
        "routes/hr.py": routes_hr_py_content,
        "routes/employee.py": routes_employee_py_content,
        "routes/attendance.py": routes_attendance_py_content,
        "routes/employee_advanced.py": routes_employee_advanced_py_content,
        "routes/urls.py": routes_urls_py_content,
        "routes/permissions.py": routes_permissions_py_content,
        "routes/documents.py": routes_documents_py_content,
        "models/__init__.py": models_init_py_content,
        "models/user.py": models_user_py_content,
        "models/company.py": models_company_py_content,
        "models/employee.py": models_employee_py_content,
        "models/attendance.py": models_attendance_py_content,
        "models/permission.py": models_permission_py_content,
        "models/department.py": models_department_py_content,
        "models/filter.py": models_filter_py_content,
        "models/urls.py": models_urls_py_content,
        "models/employee_address.py": models_employee_address_py_content,
        "models/employee_bank.py": models_employee_bank_py_content,
        "models/employee_documents.py": models_employee_documents_py_content,
        "leave/__init__.py": leave_init_py_content,
        "leave/models.py": leave_models_py_content,
        "leave/routes.py": leave_routes_py_content,
        "utils/__init__.py": "",
        "utils/decorators.py": utils_decorators_py_content,
        "utils/url_generator.py": utils_url_generator_py_content,
    }

    # 2. Create/update all the correct files
    print("\n--- Writing correct files ---")
    for path, content in project_files.items():
        create_file(path, content)

    # 3. Move all other root-level .py scripts to a 'scripts' directory
    print("\n--- Moving helper scripts ---")
    scripts_dir = "scripts"
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
    
    root_py_files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.py')]
    core_app_files = ['app.py', 'config.py', 'organize_project.py']

    for script in root_py_files:
        if script not in core_app_files:
            try:
                shutil.move(script, os.path.join(scripts_dir, script))
                print(f"🚚 Moved '{script}' to '{scripts_dir}/'")
            except Exception as e:
                print(f"❌ Could not move '{script}': {e}")

    # 4. Define and delete all obsolete/conflicting paths
    print("\n--- Deleting obsolete files and directories ---")
    obsolete_paths = [
        'auth', 
        'superadmin', 
        'employee',
        'routes.py', 
        'models.py', 
        '__init__.py',
        'models/admin.py',
        'models/hr.py',
        'models/routes.py',
        'models/permissions.py',
        'models/employee_advanced.py',
        'routes/documents_routes.py' # Old name
    ]
    for path in obsolete_paths:
        delete_path(path)

    print("\n✨ Project organization complete!")
    print("👉 You can now run 'python app.py' to start the server.")
    print("👉 It is safe to delete 'organize_project.py' now.")

if __name__ == '__main__':
    organize_project()