from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime
from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required
from utils.email_utils import send_account_created_alert, send_login_credentials
from utils.url_generator import build_web_address, build_common_login_url

superadmin_bp = Blueprint('superadmin', __name__)

# =========================================================
# 1) CREATE COMPANY (ONLY company) - YOUR REQUIRED FLOW ✅
# =========================================================
@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json() or {}

    # Required company fields
    required_fields = ['company_name', 'subdomain']
    missing = [k for k in required_fields if not data.get(k)]
    if missing:
        return jsonify({'message': f"Missing required fields: {missing}"}), 400

    # Prevent duplicate subdomain (recommended)
    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({'message': 'Subdomain already exists'}), 409

    new_company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain']
    )

    # Optional fields (only set if Company model has those attributes)
    optional_fields = [
        'company_code', 'industry', 'company_size',
        'state', 'country', 'city_branch', 'timezone'
    ]
    for field in optional_fields:
        if field in data and hasattr(Company, field):
            setattr(new_company, field, data.get(field))

    db.session.add(new_company)
    db.session.commit()

    return jsonify({
        'message': 'Company created successfully',
        'company_id': new_company.id
    }), 201


# =========================================================
# 2) CREATE ADMIN (AFTER company exists) ✅
# =========================================================
@superadmin_bp.route('/create-admin', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_admin():
    data = request.get_json() or {}

    required_fields = ['company_id', 'company_email', 'password', 'first_name', 'last_name']
    missing = [k for k in required_fields if not data.get(k)]
    if missing:
        return jsonify({'message': f"Missing required fields: {missing}"}), 400

    company = Company.query.get(data['company_id'])
    if not company:
        return jsonify({'message': 'Company not found'}), 404

    company_email = data['company_email'].strip().lower()

    if User.query.filter_by(email=company_email).first():
        return jsonify({'message': 'Email already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(
        email=company_email,
        password=hashed_password,
        role='ADMIN',
        company_id=company.id,
        status='ACTIVE'
    )
    db.session.add(new_user)
    db.session.flush()

    # Employee code generation
    emp_count = Employee.query.filter_by(company_id=company.id).count()
    emp_code = f"{company.company_code}-ADMIN-{emp_count + 1:02d}" if getattr(company, "company_code", None) else f"ADMIN-{emp_count + 1:02d}"

    new_employee = Employee(
        user_id=new_user.id,
        company_id=company.id,
        company_code=getattr(company, "company_code", None),
        employee_id=emp_code,
        first_name=data['first_name'],
        last_name=data['last_name'],
        company_email=company_email,
        personal_email=data.get('personal_email'),
        department=data.get('department', 'Administration'),
        designation=data.get('designation', 'Company Admin'),
        date_of_joining=datetime.utcnow().date()
    )
    db.session.add(new_employee)
    db.session.commit()

    # Send mails (only if personal_email is provided)
    if data.get('personal_email'):
        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)

        send_account_created_alert(data['personal_email'], company.company_name, "Super Admin")
        send_login_credentials(
            personal_email=data['personal_email'],
            company_email=company_email,
            password=data['password'],
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by="Super Admin"
        )

    return jsonify({
        'message': 'Company Admin created successfully',
        'company_id': company.id,
        'admin_user_id': new_user.id,
        'employee_id': emp_code
    }), 201


# =========================================================
# 3) GET ALL SUPER ADMINS ✅
# =========================================================
@superadmin_bp.route('/all', methods=['GET'])
@token_required
@role_required(['SUPER_ADMIN'])
def get_all_superadmins():
    superadmins = User.query.filter_by(role='SUPER_ADMIN').all()

    result = []
    for user in superadmins:
        result.append({
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "company_id": user.company_id,
            "created_at": user.created_at.isoformat() if getattr(user, 'created_at', None) else None
        })

    return jsonify({
        "count": len(result),
        "super_admins": result
    }), 200
