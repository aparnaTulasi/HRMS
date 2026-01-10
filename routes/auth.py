from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user
from datetime import datetime, timedelta
import jwt
import random
import string

from models import db
from models.user import User
from models.company import Company
from models.employee import Employee

auth_bp = Blueprint('auth', __name__)

# --------------------------------------------------
# Role → Allowed Modules (Frontend routing)
# --------------------------------------------------
def get_allowed_modules(role):
    return {
        "SUPER_ADMIN": ["dashboard", "companies", "users", "reports", "settings"],
        "ADMIN": ["dashboard", "employees", "attendance", "leave", "documents", "reports"],
        "HR": ["dashboard", "employees", "attendance", "leave", "documents"],
        "EMPLOYEE": ["dashboard", "profile", "attendance", "leave", "documents"]
    }.get(role, [])


# --------------------------------------------------
# Super Admin Signup (ONLY ONCE IN SYSTEM)
# --------------------------------------------------
@auth_bp.route('/super-admin/signup', methods=['POST'])
def signup_super_admin():
    data = request.get_json()

    if User.query.filter_by(role="SUPER_ADMIN").first():
        return jsonify({"message": "Super Admin already exists"}), 403

    # Ensure System Company
    system_company = Company.query.filter_by(company_code="SYS").first()
    if not system_company:
        system_company = Company(
            company_name="System",
            subdomain="sys.hrms.com",
            company_code="SYS"
        )
        db.session.add(system_company)
        db.session.flush()

    hashed_password = generate_password_hash(data["password"])

    super_admin = User(
        email=data["email"],
        password=hashed_password,
        role="SUPER_ADMIN",
        company_id=system_company.id,
        is_active=True
    )

    db.session.add(super_admin)
    db.session.flush()

    # Create Employee profile for Super Admin
    super_admin_employee = Employee(
        user_id=super_admin.id,
        company_id=system_company.id,
        first_name=data.get("first_name", "System"),
        last_name=data.get("last_name", "Administrator"),
        department="Management",
        designation="Super Admin",
        date_of_joining=datetime.utcnow()
    )
    db.session.add(super_admin_employee)
    db.session.commit()

    return jsonify({"message": "Super Admin registered successfully"}), 201


# --------------------------------------------------
# Company Registration (Admin Signup)
# --------------------------------------------------
@auth_bp.route('/register-company', methods=['POST'])
def register_company():
    data = request.get_json()

    # Basic Validation
    required = ['company_name', 'subdomain', 'email', 'password', 'first_name', 'last_name']
    if not all(k in data for k in required):
        return jsonify({"message": "Missing required fields"}), 400

    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({"message": "Subdomain already exists"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already registered"}), 400

    # Generate Company Code (4 digits)
    company_code = ''.join(random.choices(string.digits, k=4))

    # Create Company
    new_company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain'],
        company_code=company_code
    )
    db.session.add(new_company)
    db.session.flush()

    # Create Admin User
    hashed_password = generate_password_hash(data['password'])
    new_admin = User(
        email=data['email'],
        password=hashed_password,
        role="ADMIN",
        company_id=new_company.id,
        is_active=True
    )
    db.session.add(new_admin)
    db.session.flush()

    # Create Employee Profile
    admin_employee = Employee(
        user_id=new_admin.id,
        company_id=new_company.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        department="Management",
        designation="Admin",
        date_of_joining=datetime.utcnow()
    )
    db.session.add(admin_employee)

    db.session.commit()

    return jsonify({
        "message": "Company registered successfully",
        "company": {
            "name": new_company.company_name,
            "subdomain": new_company.subdomain,
            "code": new_company.company_code
        }
    }), 201


# --------------------------------------------------
# Login API (STRICT URL + CLEAN JWT)
# --------------------------------------------------
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"message": "Account is deactivated"}), 403

    if not user.company:
        return jsonify({"message": "User not mapped to company"}), 400

    # 🔒 STRICT URL RULE
    username = user.email.split("@")[0]
    company = user.company
    if user.role == 'SUPER_ADMIN':
        base_url = f"http://{username}.sys.hrms.com"
    else:
        base_url = f"http://{username}{company.company_code}.{company.subdomain}"

    # 🔐 JWT → ONLY identity
    token = jwt.encode(
        {
            "user_id": user.id,
            "role": user.role,
            "company_id": user.company_id,
            "exp": datetime.utcnow() + timedelta(hours=8)
        },
        current_app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "role": user.role,
        "base_url": base_url,
        "modules": get_allowed_modules(user.role),
        "user": {
            "id": user.id,
            "email": user.email,
            "username": username
        }
    }), 200