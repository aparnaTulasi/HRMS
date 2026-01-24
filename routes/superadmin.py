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
from utils.email_utils import send_login_credentials
from utils.url_generator import build_web_host, clean_domain

superadmin_bp = Blueprint("superadmin", __name__)

# ---------------------------
# Helpers
# ---------------------------
def generate_company_code(name: str) -> str:
    clean = ''.join(ch for ch in (name or "") if ch.isalnum())
    prefix = (clean[:2] or "CO").upper()
    suffix = ''.join(secrets.choice(string.digits) for _ in range(2))
    return f"{prefix}{suffix}"

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

    if not data.get("company_id") or not data.get("email") or not data.get("password"):
        return jsonify({"message": "company_id, email, and password are required"}), 400

    company = Company.query.get(data["company_id"])
    if not company:
        return jsonify({"message": "Company not found"}), 404

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 409

    try:
        raw_password = data["password"]
        hashed_password = generate_password_hash(raw_password, method="pbkdf2:sha256")

        new_admin = User(
            email=email,
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
            first_name=data.get("first_name", "Admin"),
            last_name=data.get("last_name", "User"),
            department="Management",
            designation="Admin",
            date_of_joining=datetime.utcnow()
        )
        db.session.add(admin_emp)
        db.session.commit()

        creator_host = build_web_host(g.user.email, company)
        email_sent = send_login_credentials(email, raw_password, creator_host, "Super Admin")

        return jsonify({
            "message": "Admin created successfully",
            "admin_email": email,
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

    if not data.get("company_id") or not data.get("email") or not data.get("role"):
        return jsonify({"message": "company_id, email, role are required"}), 400

    company = Company.query.get(data["company_id"])
    if not company:
        return jsonify({"message": "Company not found"}), 404

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 409

    role = data["role"].strip().upper()

    try:
        if 'password' in data and data['password']:
            raw_password = data['password']
        else:
            raw_password = secrets.token_urlsafe(12)
        hashed_password = generate_password_hash(raw_password, method="pbkdf2:sha256")

        new_user = User(
            email=email,
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
            first_name=data.get("first_name", role.title()),
            last_name=data.get("last_name", "User"),
            department=data.get("department"),
            designation=data.get("designation", role),
            date_of_joining=datetime.utcnow()
        )
        db.session.add(emp)
        db.session.commit()

        creator_host = build_web_host(g.user.email, company)
        email_sent = send_login_credentials(email, raw_password, creator_host, "Super Admin")

        return jsonify({
            "message": f"{role} created successfully",
            "email": email,
            "email_sent": email_sent
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating user", "error": str(e)}), 500
