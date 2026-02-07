from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
import secrets
import string
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required
from utils.email_utils import send_login_credentials, send_account_created_alert
from utils.url_generator import clean_domain, build_web_address, build_common_login_url

superadmin_bp = Blueprint("superadmin", __name__)

# ---------------------------
# Helpers
# ---------------------------
def generate_company_code(name: str) -> str:
    clean = ''.join(ch for ch in (name or "") if ch.isalnum())
    prefix = (clean[:2] or "CO").upper()
    suffix = ''.join(secrets.choice(string.digits) for _ in range(2))
    return f"{prefix}{suffix}"

def _generate_employee_id(company_id):
    """Generates a new unique employee ID like 'COMPCODE-0001'."""
    company = Company.query.get(company_id)
    prefix = company.company_code if company and company.company_code else "EMP"

    # Find the last employee for this company to determine the next number
    last_employee = Employee.query.filter(Employee.employee_id.like(f"{prefix}-%")).order_by(db.desc(Employee.id)).first()

    if last_employee and last_employee.employee_id:
        try:
            last_num = int(last_employee.employee_id.split('-')[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            # Fallback: count existing employees for that company
            next_num = Employee.query.filter_by(company_id=company_id).count() + 1
    else:
        # First employee
        next_num = 1
    return f"{prefix}-{next_num:04d}"


# ======================================================
# ✅ 1) CREATE COMPANY (ONLY company, NO admin)
# POST /api/superadmin/create-company
# ======================================================
@superadmin_bp.route("/create-company", methods=["POST"])
@token_required
@role_required(["SUPER_ADMIN"])
def create_company():
    data = request.get_json(force=True)

    required = ["company_name", "subdomain", "company_size", "industry", "state", "country", "city_branch"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"message": f"Missing fields: {', '.join(missing)}"}), 400

    subdomain = clean_domain(data["subdomain"])
    company_code = data.get("company_code") or generate_company_code(data["company_name"])

    # Check for duplicates
    if Company.query.filter_by(subdomain=subdomain).first():
        return jsonify({"message": "Subdomain already exists"}), 409
    if Company.query.filter_by(company_code=company_code).first():
        return jsonify({"message": "Company code already exists"}), 409

    try:
        new_company = Company(
            company_name=data["company_name"],
            subdomain=subdomain,
            company_code=company_code,

            company_size=data.get("company_size"),
            industry=data.get("industry"),
            state=data.get("state"),
            country=data.get("country"),
            city_branch=data.get("city_branch"),
            timezone=data.get("timezone", "UTC"),
        )

        db.session.add(new_company)
        db.session.commit()

        return jsonify({
            "message": "Company created successfully",
            "company_id": new_company.id,
            "company_code": new_company.company_code
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"message": "Duplicate company_code or subdomain", "error": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating company", "error": str(e)}), 500


# ======================================================
# ✅ 2) CREATE ADMIN (AFTER company create)
# POST /api/superadmin/create-admin
# ======================================================
@superadmin_bp.route("/create-admin", methods=["POST"])
@token_required
@role_required(["SUPER_ADMIN"])
def create_admin():
    data = request.get_json(force=True)

    if not data.get("company_id") or not data.get("company_email") or not data.get("password") or not data.get("personal_email"):
        return jsonify({"message": "company_id, company_email, personal_email, and password are required"}), 400

    company = Company.query.get(data["company_id"])
    if not company:
        return jsonify({"message": "Company not found"}), 404

    company_email = data["company_email"].strip().lower()
    personal_email = data["personal_email"].strip().lower()

    if User.query.filter_by(email=company_email).first():
        return jsonify({"message": "User with this company email already exists"}), 409

    try:
        raw_password = data["password"]
        hashed_password = generate_password_hash(raw_password)

        new_admin = User(
            email=company_email,
            password=hashed_password,
            role="ADMIN",
            company_id=company.id,
            is_active=True
        )
        db.session.add(new_admin)

        db.session.flush()

        admin_emp = Employee(
            user_id=new_admin.id,
            company_id=company.id,
            company_code=company.company_code,
            employee_id=_generate_employee_id(company.id),
            first_name=data.get("first_name", "Admin"),
            last_name=data.get("last_name", "User"),
            department=data.get("department", "Management"),
            designation=data.get("designation", "Admin"),
            date_of_joining=datetime.utcnow(),
            personal_email=personal_email,
            company_email=company_email
        )
        db.session.add(admin_emp)
        db.session.commit()

        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        created_by = "Super Admin"

        # Mail 1: Account Created
        send_account_created_alert(personal_email, company.company_name, created_by)

        # Mail 2: Login Credentials
        email_sent = send_login_credentials(
            personal_email=personal_email,
            company_email=company_email,
            password=raw_password,
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by=created_by
        )

        return jsonify({
            "message": "Admin created successfully",
            "employee_id": admin_emp.employee_id,
            "company_email": company_email,
            "personal_email": personal_email,
            "email_sent": email_sent
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating admin", "error": str(e)}), 500


# ======================================================
# ✅ 3) CREATE USERS (MANAGER/HR/EMPLOYEE)
# POST /api/superadmin/users
# ======================================================
@superadmin_bp.route("/users", methods=["POST"])
@token_required
@role_required(["SUPER_ADMIN"])
def create_user():
    data = request.get_json(force=True)

    if not data.get("company_id") or not data.get("company_email") or not data.get("personal_email") or not data.get("role"):
        return jsonify({"message": "company_id, company_email, personal_email, and role are required"}), 400

    company = Company.query.get(data["company_id"])
    if not company:
        return jsonify({"message": "Company not found"}), 404

    company_email = data["company_email"].strip().lower()
    personal_email = data["personal_email"].strip().lower()
    if User.query.filter_by(email=company_email).first():
        return jsonify({"message": "User with this company email already exists"}), 409

    role = data["role"].strip().upper()

    try:
        # Auto-generate password if not provided
        if 'password' in data and data['password']:
            raw_password = data['password']
        else:
            raw_password = secrets.token_urlsafe(12)
        hashed_password = generate_password_hash(raw_password)

        new_user = User(
            email=company_email,
            password=hashed_password,
            role=role,
            company_id=company.id,
            is_active=True
        )
        db.session.add(new_user)
        db.session.flush()

        emp = Employee(
            user_id=new_user.id,
            company_id=company.id,
            company_code=company.company_code,
            employee_id=_generate_employee_id(company.id),
            first_name=data.get("first_name", role.title()),
            last_name=data.get("last_name", "User"),
            department=data.get("department"),
            designation=data.get("designation", role),
            date_of_joining=datetime.utcnow(),
            personal_email=personal_email,
            company_email=company_email
        )
        db.session.add(emp)
        db.session.commit()

        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        
        email_sent = send_login_credentials(
            personal_email=personal_email,
            company_email=company_email,
            password=raw_password,
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by="Super Admin"
        )

        return jsonify({
            "message": f"{role} created successfully",
            "employee_id": emp.employee_id,
            "company_email": company_email,
            "personal_email": personal_email,
            "email_sent": email_sent
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating user", "error": str(e)}), 500
