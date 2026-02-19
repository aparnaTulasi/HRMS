from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
import jwt
from config import Config
import secrets
import string
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from models.department import Department
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

def parse_date(val):
    if not val:
        return None
    try:
        # Handles both "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS.sssZ"
        return datetime.strptime(val.split('T')[0], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

def _generate_employee_id(company_id):
    """Generates a new unique employee ID like 'COMPCODE-0001'."""
    company = Company.query.get(company_id)
    prefix = company.company_code if company and company.company_code else "EMP"

    # Find the last employee for this company to determine the next number
    # Query only specific columns to prevent schema mismatch errors (e.g., missing full_name column)
    last_employee = db.session.query(Employee.id, Employee.employee_id).filter(Employee.employee_id.like(f"{prefix}-%")).order_by(db.desc(Employee.id)).first()
    
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


def _get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.replace("Bearer ", "").strip()
    return None

def _require_super_admin():
    token = _get_bearer_token()
    if not token:
        return jsonify({"success": False, "message": "Token is missing"}), 401
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return jsonify({"success": False, "message": "Invalid token"}), 401
    role = (payload.get("role") or "").upper()
    if role not in ["SUPER_ADMIN", "SUPERADMIN", "SUPER-ADMIN"]:
        return jsonify({"success": False, "message": "Forbidden: Super Admin only"}), 403
    return None

def _slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = "".join(ch if (ch.isalnum() or ch in ["-", " "]) else "" for ch in s)
    s = "-".join([p for p in s.split() if p])
    return (s[:50] or "company")

def _unique_subdomain(base: str) -> str:
    sub = base
    i = 2
    while Company.query.filter_by(subdomain=sub).first():
        sub = f"{base}-{i}"
        i += 1
    return sub

def _split_name(fullname):
    parts = (fullname or "").strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""

# ======================================================
# ✅ 1) CREATE COMPANY (ONLY company, NO admin)
# POST /api/superadmin/create-company
# ======================================================
@superadmin_bp.route("/create-company", methods=["POST"])
def create_company():
    guard = _require_super_admin()
    if guard:
        return guard

    data = request.get_json(silent=True) or {}

    # Your frontend modal sends: name/email/address
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    address = data.get("address")

    if not name:
        return jsonify({"success": False, "message": "name is required"}), 400

    # Check if company name exists
    if Company.query.filter_by(company_name=name).first():
        return jsonify({"success": False, "message": "Company name already exists"}), 409

    # Check if email exists (if provided)
    if email and Company.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Company email already exists"}), 409

    # Check if company_code exists (if provided)
    provided_code = (data.get("company_id") or data.get("company_code") or data.get("company_Id") or "").strip()
    final_code = None

    if provided_code:
        if Company.query.filter(
            (Company.company_code == provided_code) | (Company.company_id == provided_code)
        ).first():
            return jsonify({"success": False, "message": "Company ID or Code already exists"}), 409
        final_code = provided_code
    else:
        final_code = generate_company_code(name)

    # Fill required DB fields safely
    subdomain = _unique_subdomain(_slugify(name))

    company = Company(
        company_name=name,
        subdomain=subdomain,
        company_prefix=(final_code[:3] if final_code else "EMP").upper(),
        email=email,
        address=address,
        # optional defaults (safe)
        industry=data.get("industry"),
        company_size=data.get("company_size"),
        country=data.get("country"),
        state=data.get("state"),
        city_branch=data.get("city_branch"),
        timezone=data.get("timezone") or "Asia/Kolkata",
        company_id=final_code,
        company_code=final_code
    )

    db.session.add(company)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Company created successfully",
        "data": {
            "id": company.id,
            "company_id": company.company_id,
            "name": company.company_name,
            "email": company.email,
            "address": company.address,
            "status": getattr(company, "status", None) or "Active"
        }
    }), 201


# ======================================================
# ✅ 2) CREATE ADMIN (AFTER company create)
# POST /api/superadmin/create-admin
# ======================================================
@superadmin_bp.route("/create-admin", methods=["POST"])
@token_required
@role_required(["SUPER_ADMIN", "ADMIN"])
def create_admin():
    data = request.get_json(force=True)

    # Required fields validation
    required_fields = [
        "company_id", "company_name", "full_name", "personal_email", 
        "company_email", "password", "confirm_password", "department", 
        "designation", "pay_grade", "ctc", "phone_number"
    ]
    
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    # Validate CTC is a number
    try:
        ctc_val = float(data["ctc"])
    except (ValueError, TypeError):
        return jsonify({"message": "CTC must be a number"}), 400

    identifier = str(data["company_id"]).strip()
    company = None
    if identifier.isdigit():
        company = Company.query.get(int(identifier))
    
    if not company:
        company = Company.query.filter(func.lower(Company.company_code) == identifier.lower()).first()

    if not company:
        c_name = data.get("company_name") or data.get("name")
        if c_name:
            company = Company.query.filter(func.lower(Company.company_name) == c_name.strip().lower()).first()

    if not company:
        return jsonify({"message": "Company not found"}), 404

    # If the user is an ADMIN, they can only create admins for their own company.
    if g.user.role == 'ADMIN' and company.id != g.user.company_id:
        return jsonify({"message": "Permission denied: You can only create admins for your own company."}), 403

    if data["password"] != data["confirm_password"]:
        return jsonify({"message": "Passwords do not match"}), 400

    company_email = data["company_email"].strip().lower()
    personal_email = data["personal_email"].strip().lower()

    existing_user = User.query.filter_by(email=company_email).first()
    if existing_user:
        # Provide a more helpful error if the user is soft-deleted
        if hasattr(existing_user, 'status') and existing_user.status == 'DELETED':
            return jsonify({
                "message": "This email belongs to a soft-deleted user. To use this email, you must either permanently delete the old user (using ?force=true) or choose a different email."
            }), 409
        else:
            return jsonify({"message": "User with this company email already exists"}), 409

    try:
        raw_password = data["password"]
        hashed_password = generate_password_hash(raw_password)

        new_admin = User(
            email=company_email,
            password=hashed_password,
            role="ADMIN",
            company_id=company.id,
            status="ACTIVE"
        )
        db.session.add(new_admin)

        db.session.flush()

        admin_emp = Employee(
            user_id=new_admin.id,
            company_id=company.id,
            employee_id=_generate_employee_id(company.id),
            full_name=data.get("full_name"),
            personal_email=data.get("personal_email"),
            company_email=data.get("company_email"),
            phone_number=data.get("phone_number"),
            department=data["department"],
            designation=data["designation"],
            pay_grade=data.get("pay_grade"),
            ctc=float(data.get("ctc", 0.0)),
            employment_type=data.get("employment_type"),
            gender=data.get("gender"),
            date_of_birth=parse_date(data.get("date_of_birth")),
            date_of_joining=parse_date(data.get("date_of_joining")),
            manager_id=data.get("manager_id"),
        )
        db.session.add(admin_emp)

        # Sync requested: employees.company_email ↔ users.email
        new_admin.email = admin_emp.company_email

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
@role_required(["SUPER_ADMIN", "ADMIN"])
def create_user():
    data = request.get_json(force=True)

    # Required fields validation for user creation as well
    required_fields = [
        "company_id", "full_name", "personal_email", 
        "company_email", "department", "designation", 
        "pay_grade", "ctc", "phone_number"
    ]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        ctc_val = float(data["ctc"])
    except (ValueError, TypeError):
        return jsonify({"message": "CTC must be a number"}), 400

    if data.get("password") and data.get("password") != data.get("confirm_password"):
        return jsonify({"message": "Passwords do not match"}), 400

    identifier = str(data["company_id"]).strip()
    company = None
    if identifier.isdigit():
        company = Company.query.get(int(identifier))
    
    if not company:
        company = Company.query.filter(func.lower(Company.company_code) == identifier.lower()).first()

    if not company:
        c_name = data.get("company_name") or data.get("name")
        if c_name:
            company = Company.query.filter(func.lower(Company.company_name) == c_name.strip().lower()).first()

    if not company:
        return jsonify({"message": "Company not found"}), 404

    # If the user is an ADMIN, they can only create users for their own company.
    if g.user.role == 'ADMIN' and company.id != g.user.company_id:
        return jsonify({"message": "Permission denied: You can only create users for your own company."}), 403

    company_email = data["company_email"].strip().lower()
    personal_email = data["personal_email"].strip().lower()
    existing_user = User.query.filter_by(email=company_email).first()
    if existing_user:
        # Provide a more helpful error if the user is soft-deleted
        if hasattr(existing_user, 'status') and existing_user.status == 'DELETED':
            return jsonify({
                "message": "This email belongs to a soft-deleted user. To use this email, you must either permanently delete the old user (using ?force=true) or choose a different email."
            }), 409
        else:
            return jsonify({"message": "User with this company email already exists"}), 409

    # Default to EMPLOYEE if role not provided
    role = (data.get("role") or "EMPLOYEE").strip().upper()

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
            status="ACTIVE"
        )
        db.session.add(new_user)
        db.session.flush()

        emp = Employee(
            user_id=new_user.id,
            company_id=company.id,
            employee_id=_generate_employee_id(company.id),
            full_name=data.get("full_name"),
            personal_email=data.get("personal_email"),
            company_email=data.get("company_email"),
            phone_number=data.get("phone_number"),
            department=data["department"],
            designation=data["designation"],
            pay_grade=data.get("pay_grade"),
            ctc=float(data.get("ctc", 0.0)),
            employment_type=data.get("employment_type"),
            gender=data.get("gender"),
            date_of_birth=parse_date(data.get("date_of_birth")),
            date_of_joining=parse_date(data.get("date_of_joining")),
            manager_id=data.get("manager_id"),
        )
        db.session.add(emp)

        # Sync requested: employees.company_email ↔ users.email
        new_user.email = emp.company_email

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


# ======================================================
# ✅ 4) OPTION A & B: Company + Users / Add Users
# ======================================================

def _generate_temp_password(length: int = 10) -> str:
    """Generates a strong temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def _create_user_for_company(company_id: int, u: dict):
    """
    Creates user record linked to company + sends email.
    """
    email = (u.get("email") or "").strip().lower()
    role = (u.get("role") or "").strip().upper()
    name = (u.get("name") or "").strip()

    if not email:
        return {"ok": False, "error": "User email is required"}, None

    if role not in ["ADMIN", "HR", "MANAGER"]:
        return {"ok": False, "error": "Invalid role. Allowed: ADMIN, HR, MANAGER"}, None

    # Check duplicate email
    if User.query.filter_by(email=email).first():
        return {"ok": False, "error": f"User already exists: {email}"}, None

    temp_password = _generate_temp_password(10)
    hashed_password = generate_password_hash(temp_password)

    # 1. Create User
    user = User(
        email=email,
        password=hashed_password,
        role=role,
        company_id=company_id,
        status="ACTIVE"
    )
    db.session.add(user)
    db.session.flush()

    # 2. Create Employee (Required for name storage)
    company = Company.query.get(company_id)

    emp = Employee(
        user_id=user.id,
        company_id=company_id,
        employee_id=_generate_employee_id(company_id),
        full_name=name,
        department="Management",
        designation=role,
        date_of_joining=datetime.utcnow(),
        personal_email=email
    )
    db.session.add(emp)

    # 3. Send Email
    email_sent = False
    try:
        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        
        send_login_credentials(
            personal_email=email,
            company_email=email,
            password=temp_password,
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by="Super Admin"
        )
        email_sent = True
    except Exception as e:
        print(f"Email sending failed for {email}: {e}")

    return {
        "ok": True,
        "id": user.id,
        "email": email,
        "role": role,
        "name": name,
        "email_sent": email_sent
    }, user


# POST /api/superadmin/companies
# Option A: Create company + optional users
@superadmin_bp.route("/companies", methods=["POST"])
@token_required
@role_required(["SUPER_ADMIN"])
def superadmin_create_company_with_optional_users():
    data = request.get_json(force=True)

    # Reuse existing create_company logic or create new company object
    # Here we implement a streamlined creation
    required = ["company_name", "subdomain", "company_size", "industry", "country"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    subdomain = clean_domain(data["subdomain"])
    if Company.query.filter_by(subdomain=subdomain).first():
        return jsonify({"success": False, "message": "Subdomain already exists"}), 409

    timezone = (data.get("timezone") or "Asia/Kolkata").strip()
    try:
        company = Company(
            company_name=data["company_name"],
            subdomain=subdomain,
            company_code=data.get("company_code") or generate_company_code(data["company_name"]),
            company_size=data.get("company_size"),
            industry=data.get("industry"),
            state=data.get("state"),
            country=data.get("country"),
            city_branch=data.get("city_branch"),
            address=data.get("address"),
            phone=data.get("phone"),
            email=data.get("email"),
            timezone=timezone
        )
        db.session.add(company)
        db.session.flush()

        users_payload = data.get("users") or []
        created_users = []
        failed_users = []

        for u in users_payload:
            result, _ = _create_user_for_company(company.id, u)
            if result["ok"]:
                created_users.append(result)
            else:
                failed_users.append(result)

        if failed_users:
            db.session.rollback()
            return jsonify({
                "success": False, 
                "message": "Company not created because user creation failed", 
                "errors": failed_users
            }), 400

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Company created successfully",
            "data": {
                "company_id": company.id,
                "company_name": company.company_name,
                "timezone": company.timezone,
                "created_users": created_users
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error", "error": str(e)}), 500


# POST /api/superadmin/companies/<company_id>/users
# Option B: Add users to existing company
@superadmin_bp.route("/companies/<int:company_id>/users", methods=["POST"])
@token_required
@role_required(["SUPER_ADMIN"])
def superadmin_add_users_to_company(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({"success": False, "message": "Company not found"}), 404

    data = request.get_json(force=True)
    users_payload = data.get("users") or []

    if not isinstance(users_payload, list) or not users_payload:
        return jsonify({"success": False, "message": "users must be a non-empty list"}), 400

    created_users = []
    failed_users = []

    try:
        for u in users_payload:
            result, _ = _create_user_for_company(company.id, u)
            if result["ok"]:
                created_users.append(result)
            else:
                failed_users.append(result)

        if failed_users:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "No users created because some entries failed",
                "errors": failed_users
            }), 400

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Users created successfully",
            "data": {
                "company_id": company.id,
                "created_users": created_users
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error", "error": str(e)}), 500


# ======================================================
# ✅ 5) DELETE EMPLOYEE (Soft Delete by default)
# DELETE /api/superadmin/employees/<employee_id>
# ======================================================
@superadmin_bp.route("/employees/<employee_id>", methods=["DELETE"])
@token_required
@role_required(["SUPER_ADMIN"])
def delete_employee(employee_id):
    emp = Employee.query.filter_by(employee_id=str(employee_id)).first()

    if not emp and str(employee_id).isdigit():
        emp = Employee.query.get(int(employee_id))

    if not emp:
        return jsonify({"success": False, "message": "Employee not found"}), 404

    force = request.args.get("force", "false").lower() == "true"
    user = User.query.get(emp.user_id) if emp.user_id else None

    try:
        if not force:
            # --- SOFT DELETE ---
            if hasattr(emp, "status"):
                emp.status = "DELETED"
            if hasattr(emp, "is_active"):
                emp.is_active = False
            if user:
                if hasattr(user, "status"):
                    user.status = "DELETED"
            db.session.commit()
            return jsonify({"success": True, "message": "Employee deleted (soft delete)"}), 200

        # --- HARD DELETE (PERMANENT) ---
        # To prevent foreign key errors, we must first handle relationships
        # where this employee is a manager.

        # 1. Un-assign this manager from any employees who report to them.
        Employee.query.filter_by(manager_id=emp.id).update({"manager_id": None})

        # 2. Un-assign this manager from any departments they manage.
        # Use direct table column access to avoid any potential ORM attribute mapping issues.
        Department.query.filter(Department.__table__.c.manager_id == emp.id).update({"manager_id": None})

        # Now it's safe to delete the employee and their user record.
        db.session.delete(emp)
        if user:
            db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "Employee deleted permanently"}), 200
    except Exception as e:
        db.session.rollback()
        action = "permanently deleting" if force else "soft-deleting"
        return jsonify({"success": False, "message": f"Error {action} employee", "error": str(e)}), 500
