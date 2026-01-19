from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user
from flask_mail import Mail, Message
from models.super_admin import SuperAdmin
from datetime import datetime, timedelta
import jwt
import random
import string

from models import db
from models.user import User
from models.company import Company
from models.employee import Employee

auth_bp = Blueprint('auth', __name__)
mail = Mail()

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

    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    required = ["email", "password", "confirm_password"]
    if not all(data.get(k) for k in required):
        return jsonify({"message": "email, password, confirm_password are required"}), 400

    if data["password"] != data["confirm_password"]:
        return jsonify({"message": "Password and confirm password do not match"}), 400

    if User.query.filter_by(role="SUPER_ADMIN").first():
        return jsonify({"message": "Super Admin already exists"}), 403

    # Ensure System Company
    system_company = Company.query.filter_by(subdomain="sys.com").first()
    if not system_company:
        system_company = Company(
            company_name="System",
            subdomain="sys.com",
            company_code="SYS"
        )
        db.session.add(system_company)
        db.session.flush()

    hashed_password = generate_password_hash(data["password"])

    super_admin = User(
        email=data["email"].strip().lower(),
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
        first_name=data.get("first_name", "ragu"),
        last_name=data.get("last_name", "vamsi"),
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

    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    required = ['company_name', 'subdomain', 'company_code', 'email', 'password', 'confirm_password', 'first_name', 'last_name']
    if not all(data.get(k) for k in required):
        return jsonify({"message": "Missing required fields"}), 400

    if data["password"] != data["confirm_password"]:
        return jsonify({"message": "Password and confirm password do not match"}), 400

    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({"message": "Domain already exists"}), 400

    if Company.query.filter_by(company_code=data['company_code']).first():
        return jsonify({"message": "Company code already exists"}), 400

    if User.query.filter_by(email=data['email'].strip().lower()).first():
        return jsonify({"message": "Email already registered"}), 400

    # Create Company (✅ subdomain = full domain, custom company_code)
    new_company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain'],
        company_code=data['company_code']
    )
    db.session.add(new_company)
    db.session.flush()

    # Create Admin User
    hashed_password = generate_password_hash(data['password'])
    new_admin = User(
        email=data['email'].strip().lower(),
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
            "domain": new_company.subdomain,
            "code": new_company.company_code
        }
    }), 201


# --------------------------------------------------
# Login API (STRICT URL + CLEAN JWT)
# --------------------------------------------------
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    email = email.strip().lower()

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


# --------------------------------------------------
# Forgot Password Flow
# --------------------------------------------------
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    email = data.get("email")

    if not email:
        return jsonify({"message": "Email is required"}), 400

    email = email.strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        # For security, don't reveal if user exists
        return jsonify({"message": "If email exists, OTP sent"}), 200

    otp = ''.join(random.choices(string.digits, k=6))
    user.reset_otp = otp
    user.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    try:
        msg = Message(
            subject="HRMS Password Reset OTP",
            recipients=[email],
            body=f"Your OTP for password reset is: {otp}\nValid for 10 minutes."
        )
        mail.send(msg)
    except Exception as e:
        return jsonify({"message": "Failed to send email", "error": str(e)}), 500

    return jsonify({"message": "If email exists, OTP sent"}), 200


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_reset_otp():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    if not data.get("email") or not data.get("otp"):
        return jsonify({"message": "Email and OTP are required"}), 400

    email = data.get("email").strip().lower()
    otp = data.get("otp")

    user = User.query.filter_by(email=email).first()
    if not user or not user.reset_otp or user.reset_otp != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    if not user.reset_otp_expiry or user.reset_otp_expiry < datetime.utcnow():
        return jsonify({"message": "OTP expired"}), 400

    return jsonify({"message": "OTP verified successfully"}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    required = ["email", "otp", "password", "confirm_password"]
    if not all(data.get(k) for k in required):
        return jsonify({"message": "email, otp, password, confirm_password are required"}), 400

    email = data.get("email").strip().lower()
    otp = data.get("otp")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.reset_otp or user.reset_otp != otp:
        return jsonify({"message": "Invalid or expired OTP"}), 400

    if not user.reset_otp_expiry or user.reset_otp_expiry < datetime.utcnow():
        return jsonify({"message": "Invalid or expired OTP"}), 400

    user.password = generate_password_hash(password)
    user.reset_otp = None
    user.reset_otp_expiry = None
    db.session.commit()

    return jsonify({"message": "Password reset successfully"}), 200
