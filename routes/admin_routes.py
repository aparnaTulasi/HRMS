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
app.register_blueprint(payroll_bp, url_prefix='/api/payroll')
app.register_blueprint(leave_bp)
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
from models import db
import secrets

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')
    portal_prefix = db.Column(db.String(50), nullable=True)
    profile_completed = db.Column(db.Boolean, default=False)
    profile_locked = db.Column(db.Boolean, default=False)
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
    employeement_type = db.Column(db.String(50))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bank_details = db.relationship('EmployeeBankDetails', backref='employee', uselist=False, lazy=True)
    address = db.relationship('EmployeeAddress', backref='employee', uselist=False, lazy=True)
    documents = db.relationship('EmployeeDocument', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
    manager = db.relationship('Employee', remote_side=[id], backref='subordinates')

    education_details = db.Column(db.JSON, nullable=True)
    last_work_details = db.Column(db.JSON, nullable=True)
    statutory_details = db.Column(db.JSON, nullable=True)

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

models_payroll_py_content = """
from datetime import datetime
from models import db

class PayGrade(db.Model):
    __tablename__ = 'pay_grades'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    grade_name = db.Column(db.String(100), nullable=False)
    min_salary = db.Column(db.Float, default=0.0)
    max_salary = db.Column(db.Float, default=0.0)
    basic_pct = db.Column(db.Float, default=0.0)
    hra_pct = db.Column(db.Float, default=0.0)
    ta_pct = db.Column(db.Float, default=0.0)
    medical_pct = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

class PayRole(db.Model):
    __tablename__ = 'pay_roles'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    pay_grade_id = db.Column(db.Integer, db.ForeignKey('pay_grades.id'))
    is_active = db.Column(db.Boolean, default=True)

class Payslip(db.Model):
    __tablename__ = 'payslips'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_month = db.Column(db.Integer, nullable=False)
    pay_year = db.Column(db.Integer, nullable=False)
    pay_date = db.Column(db.Date)
    total_days = db.Column(db.Integer, default=30)
    paid_days = db.Column(db.Integer, default=30)
    lwp_days = db.Column(db.Integer, default=0)
    gross_salary = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    total_reimbursements = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)
    annual_ctc = db.Column(db.Float, default=0.0)
    monthly_ctc = db.Column(db.Float, default=0.0)
    tax_regime = db.Column(db.String(20), default="OLD")
    section_80c = db.Column(db.Float, default=0.0)
    monthly_rent = db.Column(db.Float, default=0.0)
    city_type = db.Column(db.String(20), default="NON_METRO")
    other_deductions = db.Column(db.Float, default=0.0)
    calculated_tds = db.Column(db.Float, default=0.0)
    bank_account_no = db.Column(db.String(50))
    uan_no = db.Column(db.String(50))
    esi_account_no = db.Column(db.String(50))
    status = db.Column(db.String(20), default="DRAFT")
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    pdf_path = db.Column(db.String(255))

    earnings = db.relationship('PayslipEarning', backref='payslip', lazy=True, cascade="all, delete-orphan")
    deductions = db.relationship('PayslipDeduction', backref='payslip', lazy=True, cascade="all, delete-orphan")
    employer_contribs = db.relationship('PayslipEmployerContribution', backref='payslip', lazy=True, cascade="all, delete-orphan")
    reimbursements = db.relationship('PayslipReimbursement', backref='payslip', lazy=True, cascade="all, delete-orphan")

class PayslipEarning(db.Model):
    __tablename__ = 'payslip_earnings'
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslips.id'), nullable=False)
    component = db.Column(db.String(100))
    amount = db.Column(db.Float, default=0.0)

class PayslipDeduction(db.Model):
    __tablename__ = 'payslip_deductions'
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslips.id'), nullable=False)
    component = db.Column(db.String(100))
    amount = db.Column(db.Float, default=0.0)

class PayslipEmployerContribution(db.Model):
    __tablename__ = 'payslip_employer_contributions'
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslips.id'), nullable=False)
    component = db.Column(db.String(100))
    amount = db.Column(db.Float, default=0.0)

class PayslipReimbursement(db.Model):
    __tablename__ = 'payslip_reimbursements'
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslips.id'), nullable=False)
    component = db.Column(db.String(100))
    amount = db.Column(db.Float, default=0.0)
"""

routes_payroll_py_content = """
from datetime import datetime
from flask import Blueprint, request, jsonify, g, send_file
from models import db
from utils.decorators import token_required
# from utils.payslip_pdf import generate_payslip_pdf # Uncomment when PDF util is ready

from models.payroll import (
    PayGrade, PayRole, Payslip,
    PayslipEarning, PayslipDeduction, PayslipEmployerContribution, PayslipReimbursement
)

payroll_bp = Blueprint("payroll", __name__)

def _company_id():
    return g.user.company_id

def _employee_db_id():
    if hasattr(g.user, "employee_profile") and g.user.employee_profile:
        return g.user.employee_profile.id
    return None

def _is_owner_employee(payslip):
    emp_id = _employee_db_id()
    return g.user.role == "EMPLOYEE" and emp_id == payslip.employee_id

def _replace_items(model, payslip_id, items):
    model.query.filter_by(payslip_id=payslip_id).delete()
    for it in items:
        component = (it.get("component") or "").strip()
        amount = float(it.get("amount", 0) or 0)
        if component:
            db.session.add(model(payslip_id=payslip_id, component=component, amount=amount))

@payroll_bp.route("/payslips", methods=["GET"])
@token_required
def list_payslips():
    if g.user.role not in ['ADMIN', 'HR']: return jsonify({"message": "Unauthorized"}), 403
    employee_id = request.args.get("employee_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    q = Payslip.query.filter_by(company_id=_company_id(), is_deleted=False)
    if employee_id: q = q.filter_by(employee_id=employee_id)
    if month: q = q.filter_by(pay_month=month)
    if year: q = q.filter_by(pay_year=year)

    rows = q.order_by(Payslip.id.desc()).all()
    return jsonify({"success": True, "data": [{
        "id": p.id, "employee_id": p.employee_id, "pay_month": p.pay_month, "pay_year": p.pay_year,
        "net_salary": p.net_salary, "status": p.status
    } for p in rows]})

@payroll_bp.route("/payslips", methods=["POST"])
@token_required
def create_payslip():
    if g.user.role not in ['ADMIN', 'HR']: return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json() or {}

    p = Payslip(
        company_id=_company_id(),
        employee_id=int(data["employee_id"]),
        pay_month=int(data["pay_month"]),
        pay_year=int(data["pay_year"]),
        total_days=int(data.get("total_days", 0)),
        paid_days=int(data.get("paid_days", 0)),
        lwp_days=int(data.get("lwp_days", 0)),
        gross_salary=float(data.get("gross_salary", 0)),
        total_deductions=float(data.get("total_deductions", 0)),
        net_salary=float(data.get("net_salary", 0)),
        annual_ctc=float(data.get("annual_ctc", 0)),
        monthly_ctc=float(data.get("monthly_ctc", 0)),
        tax_regime=data.get("tax_regime", "OLD"),
        status=data.get("status", "DRAFT"),
        created_by=g.user.id
    )
    if data.get("pay_date"):
        p.pay_date = datetime.strptime(data["pay_date"], "%Y-%m-%d").date()

    db.session.add(p)
    db.session.flush()

    _replace_items(PayslipEarning, p.id, data.get("earnings", []))
    _replace_items(PayslipDeduction, p.id, data.get("deductions", []))
    _replace_items(PayslipEmployerContribution, p.id, data.get("employer_contribs", []))

    db.session.commit()
    return jsonify({"success": True, "message": "Payslip created", "id": p.id})

@payroll_bp.route("/payslips/<int:payslip_id>", methods=["PUT"])
@token_required
def update_payslip(payslip_id):
    if g.user.role not in ['ADMIN', 'HR']: return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json() or {}
    p = Payslip.query.filter_by(id=payslip_id, company_id=_company_id()).first()
    if not p: return jsonify({"message": "Not found"}), 404

    if "status" in data: p.status = data["status"]
    if "net_salary" in data: p.net_salary = data["net_salary"]
    
    if "earnings" in data: _replace_items(PayslipEarning, p.id, data["earnings"])
    if "deductions" in data: _replace_items(PayslipDeduction, p.id, data["deductions"])
    
    db.session.commit()
    return jsonify({"success": True, "message": "Payslip updated"})

@payroll_bp.route("/my-payslips", methods=["GET"])
@token_required
def my_payslips():
    emp_id = _employee_db_id()
    rows = Payslip.query.filter_by(company_id=_company_id(), employee_id=emp_id, status="PUBLISHED").all()
    return jsonify({"success": True, "data": [{"id": p.id, "month": p.pay_month, "net": p.net_salary} for p in rows]})
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
from flask import Blueprint, jsonify, request, g
from werkzeug.security import generate_password_hash
from datetime import datetime
from models import db
from models.user import User
from models.company import Company
from utils.decorators import token_required, role_required
from models.employee import Employee
from utils.email_utils import send_account_created_alert, send_login_credentials
from utils.url_generator import generate_login_url
# from models.employee_onboarding_request import EmployeeOnboardingRequest # Uncomment if model exists

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN'])
def get_employees():
    if g.user.role == 'SUPER_ADMIN':
        employees = Employee.query.all()
    else:
        employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([{'id': emp.id, 'name': emp.full_name} for emp in employees])

@admin_bp.route('/create-hr', methods=['POST'])
@token_required
@role_required(['ADMIN', 'SUPER_ADMIN'])
def create_hr():
    data = request.get_json(force=True)
    email = data.get('email') or data.get('company_email')
    personal_email = data.get('personal_email')
    if not email or not data.get('password'):
        return jsonify({'message': 'Email and Password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409

    company_id = g.user.company_id
    if g.user.role == 'SUPER_ADMIN':
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'message': 'Company ID required for Super Admin'}), 400

    company = Company.query.get(company_id)
    if not company:
        return jsonify({'message': 'Company not found'}), 404

    hashed_password = generate_password_hash(data['password'])
    new_user = User(email=email, password=hashed_password, role='HR', company_id=company_id)
    db.session.add(new_user)
    db.session.flush()

    emp_count = Employee.query.filter_by(company_id=company_id).count()
    emp_code = f"{company.company_code}-{emp_count + 1:04d}"

    new_employee = Employee(
        user_id=new_user.id,
        company_id=company_id,
        employee_id=emp_code,
        full_name=data.get('full_name'),
        company_email=email,
        personal_email=personal_email,
        department=data.get('department', 'Human Resources'),
        designation=data.get('designation', 'HR Manager')
    )
    db.session.add(new_employee)
    db.session.commit()
    return jsonify({'message': 'HR created successfully'}), 201

@admin_bp.route('/create-employee', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_employee():
    data = request.get_json(force=True)
    email = data.get('email') or data.get('company_email')
    if not email: return jsonify({'message': 'Email required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409
        
    hashed_password = generate_password_hash(data.get('password', 'Password@123'))
    user = User(email=email, password=hashed_password, role='EMPLOYEE', company_id=g.user.company_id, status='ACTIVE')
    db.session.add(user)
    db.session.flush()

    company = Company.query.get(g.user.company_id)
    emp_count = Employee.query.filter_by(company_id=g.user.company_id).count()
    emp_code = f"{company.company_code}-{emp_count + 1:04d}"

    emp = Employee(
        user_id=user.id,
        company_id=g.user.company_id,
        employee_id=emp_code,
        full_name=data.get('full_name'),
        personal_email=data.get('personal_email'),
        department=data.get('department'),
        designation=data.get('designation')
    )
    db.session.add(emp)
    db.session.commit()
    return jsonify({'message': 'Employee created successfully'}), 201

@admin_bp.route('/employees/<int:emp_id>', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN'])
def get_employee(emp_id):
    if g.user.role == 'SUPER_ADMIN':
        emp = Employee.query.filter_by(id=emp_id).first()
    else:
        emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    
    if not emp: return jsonify({"message":"Employee not found"}), 404
    
    return jsonify({
        "id": emp.id,
        "employee_id": emp.employee_id,
        "full_name": emp.full_name,
        "education_details": emp.education_details,
        "last_work_details": emp.last_work_details,
        "statutory_details": emp.statutory_details
    })

@admin_bp.route('/employees/<int:emp_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN','HR', 'SUPER_ADMIN'])
def update_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id).first()
    if not emp: return jsonify({"message":"Employee not found"}), 404
    
    data = request.get_json(force=True)
    for k, v in data.items():
        if hasattr(emp, k): setattr(emp, k, v)
    
    db.session.commit()
    return jsonify({"message":"Employee updated"}), 200

@admin_bp.route('/employees/<int:emp_id>/education', methods=['POST'])
@token_required
@role_required(['ADMIN','HR'])
def save_education(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    if not emp: return jsonify({"message":"Employee not found"}), 404
    emp.education_details = request.get_json(force=True)
    db.session.commit()
    return jsonify({"message":"Education saved"}), 200
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
    return jsonify({
        'id': emp.id,
        'employee_id': emp.employee_id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'email': emp.company_email,
        'department': emp.department,
        'designation': emp.designation,
        'phone': getattr(emp, 'work_phone', None),
        'date_of_joining': emp.date_of_joining.isoformat() if emp.date_of_joining else None
        'education_details': emp.education_details,
        'last_work_details': emp.last_work_details,
        'statutory_details': emp.statutory_details
    })

@employee_bp.route('/address', methods=['POST'])
@token_required
def add_address():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID required'}), 400

    emp = Employee.query.get(emp_id)
    if not emp: return jsonify({'message': 'Employee not found'}), 404

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
    
    db.session.commit()
    return jsonify({'message': 'Bank details updated successfully'})
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
        attendance = Attendance(employee_id=emp.id, date=today, in_time=datetime.utcnow(), status='PRESENT', year=today.year, month=today.month)
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
from flask import request, jsonify
from jwt_auth import jwt_required, get_current_user
from . import leave_bp
from .models import Leave
from models import db
from datetime import datetime

@leave_bp.route('/apply', methods=['POST'])
@jwt_required
def apply_leave():
    data = request.get_json()
    user = get_current_user()
    emp = user.employee_profile
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
        "models/payroll.py": models_payroll_py_content,
        "routes/payroll.py": routes_payroll_py_content,
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