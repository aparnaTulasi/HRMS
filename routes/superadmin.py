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

@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json()
    new_company = Company(
        company_name=data['company_name'], 
        subdomain=data['subdomain'],
        company_code=data.get('company_code'),
        industry=data.get('industry'),
        company_size=data.get('company_size'),
        state=data.get('state'),
        country=data.get('country'),
        city_branch=data.get('city_branch'),
        timezone=data.get('timezone')
    )
    db.session.add(new_company)
    db.session.flush()

    if data.get('admin_email') and data.get('admin_password'):
        hashed_password = generate_password_hash(data['admin_password'], method='pbkdf2:sha256')
        new_admin = User(email=data['admin_email'], password=hashed_password, role='ADMIN', company_id=new_company.id)
        db.session.add(new_admin)
        db.session.flush()

        admin_emp = Employee(user_id=new_admin.id, company_id=new_company.id, first_name=data.get('admin_first_name', 'Admin'), last_name=data.get('admin_last_name', 'User'))
        db.session.add(admin_emp)
        db.session.commit()
        return jsonify({'message': 'Company and Admin created'}), 201

    db.session.commit()
    return jsonify({'message': 'Company created successfully'}), 201

@superadmin_bp.route('/create-admin', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_admin():
    print("🔵 Create Admin Request Received...", flush=True)
    data = request.get_json()
    
    required_fields = ['company_id', 'company_email', 'password', 'first_name', 'last_name']
    if not all(k in data for k in required_fields):
        return jsonify({'message': 'Missing required fields'}), 400

    company = Company.query.get(data['company_id'])
    if not company:
        return jsonify({'message': 'Company not found'}), 404

    if User.query.filter_by(email=data['company_email']).first():
        return jsonify({'message': 'Email already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(
        email=data['company_email'],
        password=hashed_password,
        role='ADMIN',
        company_id=company.id,
        status='ACTIVE'
    )
    db.session.add(new_user)
    db.session.flush()
    
    emp_count = Employee.query.filter_by(company_id=company.id).count()
    emp_code = f"{company.company_code}-ADMIN-{emp_count + 1:02d}" if company.company_code else f"ADMIN-{emp_count + 1:02d}"

    new_employee = Employee(
        user_id=new_user.id,
        company_id=company.id,
        company_code=company.company_code,
        employee_id=emp_code,
        first_name=data['first_name'],
        last_name=data['last_name'],
        company_email=data['company_email'],
        personal_email=data.get('personal_email'),
        department=data.get('department', 'Administration'),
        designation=data.get('designation', 'Company Admin'),
        date_of_joining=datetime.utcnow().date()
    )
    db.session.add(new_employee)
    db.session.commit()

    print(f"✅ Admin Created: {data['company_email']}", flush=True)

    if data.get('personal_email'):
        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        
        send_account_created_alert(data['personal_email'], company.company_name, "Super Admin")
        send_login_credentials(
            personal_email=data['personal_email'],
            company_email=data['company_email'],
            password=data['password'],
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by="Super Admin"
        )
        print(f"📧 Credentials sent to {data['personal_email']}", flush=True)

    return jsonify({'message': 'Company Admin created successfully'}), 201