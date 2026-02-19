from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
import secrets
import string
from sqlalchemy import text

from models import db

# Import Company model from the models package
from models.company import Company

# Try import User model (project structure can differ)
try:
    from models.user import User
except Exception:
    try:
        from user import User
    except Exception:
        User = None

# Try import Branch model
try:
    from models.branch import Branch
except ImportError:
    Branch = None

# Try import your existing email function (do NOT change its internal logic)
send_login_credentials = None
try:
    from utils.email_utils import send_login_credentials
except Exception:
    try:
        from email_utils import send_login_credentials
    except Exception:
        send_login_credentials = None

# Import ID generator utils
try:
    from id_generator import normalize_prefix
except ImportError:
    normalize_prefix = lambda x: x # Fallback if file missing

from utils.jwt_auth import jwt_required

company_bp = Blueprint("company_bp", __name__)

# @company_bp.before_request
# @jwt_required
# def load_user_from_jwt():
#     pass

# ----------------------------
# SUPER ADMIN GUARD (no auth changes)
# ----------------------------
def require_super_admin():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    role = (getattr(user, "role", "") or "").upper()
    if role not in ["SUPER_ADMIN", "SUPERADMIN", "SUPER-ADMIN"]:
        return jsonify({"success": False, "message": "Forbidden: Super Admin only"}), 403

    return None


def require_hr_access():
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    role = (getattr(user, "role", "") or "").upper()
    if role not in ["HR_MANAGER", "HR_EXECUTIVE"]:
        return jsonify({"success": False, "message": "Forbidden: HR access only"}), 403

    return None

# ----------------------------
# HELPERS
# ----------------------------
def slugify(value: str) -> str:
    s = (value or "").strip().lower()
    s = "".join(ch if (ch.isalnum() or ch in ["-", " "]) else "" for ch in s)
    s = "-".join([p for p in s.split() if p])
    return (s[:100] or "company")


def unique_subdomain(base: str) -> str:
    base = (base or "").strip().lower()
    sub = base
    i = 2
    while Company.query.filter_by(subdomain=sub).first():
        sub = f"{base}-{i}"
        i += 1
    return sub


def gen_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def normalize_role(role: str) -> str:
    r = (role or "").strip().upper()
    # UI shows "User / Manager". Map it to your system roles.
    if r == "USER":
        return "EMPLOYEE"
    if r == "ADMIN":
        return "COMPANY_ADMIN"
    if r == "HR":
        return "HR_MANAGER"

    r = r.replace(" ", "_")
    return r


def set_if_exists(obj, field: str, value):
    if hasattr(obj, field):
        setattr(obj, field, value)


def create_user_and_email(company_id: int, email: str, role: str, name: str = ""):
    """
    Creates a user linked to company + emails temp password using your existing email util.
    """
    if User is None:
        return {"ok": False, "error": "User model not found in project"}, None

    if send_login_credentials is None:
        return {"ok": False, "error": "send_login_credentials not found. Fix import in routes file."}, None

    email = (email or "").strip().lower()
    if not email:
        return {"ok": False, "error": "Invite email is required"}, None

    role = normalize_role(role)
    allowed = [
        "SUPER_ADMIN", 
        "COMPANY_ADMIN", 
        "HR_MANAGER", "HR_EXECUTIVE", 
        "MANAGER", "TEAM_LEAD", 
        "EMPLOYEE", 
        "FINANCE_ADMIN", "PAYROLL_ADMIN", 
        "RECRUITER"
    ]
    if role not in allowed:
        return {"ok": False, "error": f"Invalid role. Allowed: {', '.join(allowed)}"}, None

    # Prevent duplicates
    if User.query.filter_by(email=email).first():
        return {"ok": False, "error": f"User already exists: {email}"}, None

    temp_password = gen_temp_password(10)
    password_hash = generate_password_hash(temp_password)

    user = User()

    # Most projects have these fields; we set only if exists
    set_if_exists(user, "company_id", company_id)
    set_if_exists(user, "email", email)
    set_if_exists(user, "role", role)
    set_if_exists(user, "name", name)

    # password field varies in projects
    if hasattr(user, "password_hash"):
        user.password_hash = password_hash
    elif hasattr(user, "password"):
        user.password = password_hash
    else:
        return {"ok": False, "error": "User model has no password field (password_hash/password)"}, None

    db.session.add(user)
    db.session.flush()

    # Call your existing mail function (do not change it)
    try:
        send_login_credentials(
            user_email=email,
            password=temp_password,
            creator_web_host="",           # keep empty if you don’t use it
            created_by_role="SUPER_ADMIN"  # as per your current flow
        )
        email_sent = True
    except Exception:
        email_sent = False

    return {
        "ok": True,
        "id": getattr(user, "id", None),
        "email": email,
        "role": role,
        "name": name,
        "email_sent": email_sent
    }, user


# ----------------------------
# 1) CREATE COMPANY (Option A + B)
# POST /api/superadmin/companies
# ----------------------------
@company_bp.route("/companies", methods=["POST"])
@company_bp.route("/create-company", methods=["POST"])
def create_company():
    # guard = require_super_admin()
    # if guard:
    #     return guard

    print("AUTH HEADER:", request.headers.get("Authorization"))

    data = request.get_json(silent=True) or {}

    company_name = (data.get("company_name") or "").strip()

    # UI sends company_Id (FS001). DB column is company_code.
    company_code = (data.get("company_Id") or data.get("company_code") or "").strip().upper()
    company_prefix = (data.get("company_prefix") or "").strip().upper()

    industry = (data.get("industry") or "").strip()
    company_size = (data.get("company_size") or "").strip()
    country = (data.get("country") or "").strip()
    state = (data.get("state") or "").strip()
    city_branch = (data.get("city_branch") or "").strip()
    timezone = (data.get("timezone") or "Asia/Kolkata").strip()

    missing = []
    if not company_name: missing.append("company_name")
    if not company_code: missing.append("company_Id (company code like FS001)")
    if not industry: missing.append("industry")
    if not company_prefix: missing.append("company_prefix")
    if not company_size: missing.append("company_size")
    if not country: missing.append("country")
    if not state: missing.append("state")
    if not city_branch: missing.append("city_branch")

    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    # Check if company exists
    company = Company.query.filter_by(company_code=company_code).first()

    if not company and company_name:
        company = Company.query.filter_by(company_name=company_name).first()

    if not company and data.get("email"):
        company = Company.query.filter_by(email=data.get("email")).first()

    is_new_company = False

    if not company:
        is_new_company = True
        # subdomain can be provided from frontend, else auto-generate from company_name
        subdomain = (data.get("subdomain") or "").strip().lower()
        if not subdomain:
            subdomain = unique_subdomain(slugify(company_name))
        else:
            # Ensure uniqueness if user typed it
            if Company.query.filter_by(subdomain=subdomain).first():
                return jsonify({"success": False, "message": "subdomain already exists"}), 400

    # Optional invite (your UI has single teammate)
    invite_email = (data.get("invite_email") or "").strip()
    invite_role = (data.get("invite_role") or data.get("role") or "").strip()  # role dropdown
    invite_name = (data.get("invite_name") or "").strip()

    # Also support array for future: users:[]
    branches_payload = data.get("branches") or []
    users_payload = data.get("users") or []
    if invite_email:
        users_payload = users_payload + [{
            "email": invite_email,
            "role": invite_role or "EMPLOYEE",
            "name": invite_name
        }]

    try:
        if is_new_company:
            # Normalize prefix
            prefix = normalize_prefix(company_prefix)

            # SQLite-safe: keep company + users in one transaction
            # (BEGIN IMMEDIATE locks writes so no partial states)

            company = Company(
                company_name=company_name,
                subdomain=subdomain,
                company_code=company_code,
                company_prefix=prefix,
                company_uid=prefix + "00",
                last_user_number=0,
                industry=industry,
                company_size=company_size,
                country=country,
                state=state,
                city_branch=city_branch,
                timezone=timezone,
                address=data.get("address"),
                phone=data.get("phone"),
                email=data.get("email"),
            )
            db.session.add(company)
            db.session.flush()

        created_branches = []
        if branches_payload:
            if not Branch:
                db.session.rollback()
                return jsonify({"success": False, "message": "Branch model not found"}), 500

            for b_data in branches_payload:
                b_name = (b_data.get("branch_name") or "").strip()
                if not b_name:
                    # If branch has data but no name, fail the request to ensure data integrity
                    if b_data.get("address") or b_data.get("latitude") or b_data.get("longitude"):
                        db.session.rollback()
                        return jsonify({"success": False, "message": "Branch name is required"}), 400
                    continue
                new_branch = Branch(
                    company_id=company.id,
                    branch_name=b_name,
                    address=b_data.get("address"),
                    latitude=b_data.get("latitude"),
                    longitude=b_data.get("longitude"),
                    status=b_data.get("status", "Active")
                )
                db.session.add(new_branch)
                created_branches.append(b_data) # Storing payload for response reference

        created_users = []
        failed_users = []

        for u in users_payload:
            email = (u.get("email") or "").strip()
            role = (u.get("role") or "").strip()
            name = (u.get("name") or "").strip()
            if not email:
                continue

            res, _ = create_user_and_email(company.id, email, role, name)
            if res["ok"]:
                created_users.append(res)
            else:
                # If company exists, ignore "User already exists" error
                if not is_new_company and "already exists" in str(res.get("error", "")):
                    continue
                failed_users.append(res)

        # If you want: if invite fails, rollback company too (strong consistency)
        if failed_users:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "Company not created because user invite/user creation failed",
                "errors": failed_users
            }), 400

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Company created successfully" if is_new_company else "Company updated with new branches",
            "data": {
                "company": {
                    "id": company.id,
                    "company_name": company.company_name,
                    "company_code": company.company_code,
                    "subdomain": company.subdomain,
                    "industry": company.industry,
                    "company_size": company.company_size,
                    "country": company.country,
                    "state": company.state,
                    "city_branch": company.city_branch,
                    "timezone": company.timezone,
                    "address": company.address,
                    "phone": company.phone,
                    "email": company.email,
                },
                "created_users": created_users,
                "created_branches": created_branches
            }
        }), 201 if is_new_company else 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error", "error": str(e)}), 500


# ----------------------------
# 6) BRANCH MANAGEMENT (Super Admin)
# ----------------------------

@company_bp.route("/branches", methods=["POST"])
@jwt_required
def create_branch():
    guard = require_super_admin()
    if guard: return guard

    if not Branch:
        return jsonify({"success": False, "message": "Branch model not found"}), 500

    data = request.get_json(silent=True) or {}
    
    company_id = data.get("company_id")
    branch_name = (data.get("branch_name") or "").strip()

    if not company_id:
        return jsonify({"success": False, "message": "company_id is required"}), 400
    if not branch_name:
        return jsonify({"success": False, "message": "branch_name is required"}), 400

    # Check if company exists
    company = Company.query.get(company_id)
    if not company:
        return jsonify({"success": False, "message": "Company not found"}), 404

    new_branch = Branch(
        company_id=company_id,
        branch_name=branch_name,
        address=data.get("address"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        status=data.get("status", "Active")
    )
    db.session.add(new_branch)
    db.session.commit()

    branch_data = { "id": new_branch.id, "company_id": new_branch.company_id, "branch_name": new_branch.branch_name, "address": new_branch.address, "latitude": new_branch.latitude, "longitude": new_branch.longitude, "status": new_branch.status }

    return jsonify({
        "success": True, 
        "message": "Branch created successfully",
        "data": branch_data
    }), 201


@company_bp.route("/branches", methods=["GET"])
@jwt_required
def list_branches():
    guard = require_super_admin()
    if guard: return guard

    if not Branch:
        return jsonify({"success": False, "message": "Branch model not found"}), 500

    # Join Branch with Company to get company name
    results = db.session.query(Branch, Company).join(Company, Branch.company_id == Company.id).order_by(Branch.id.desc()).all()

    data = []
    for b, c in results:
        data.append({
            "id": b.id,
            "branch_name": b.branch_name,
            "company_name": c.company_name,
            "address": b.address,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "status": b.status
        })
    
    return jsonify({"success": True, "data": data}), 200


@company_bp.route("/branches/<int:branch_id>", methods=["GET"])
@jwt_required
def get_branch(branch_id):
    guard = require_super_admin()
    if guard: return guard

    if not Branch:
        return jsonify({"success": False, "message": "Branch model not found"}), 500

    # Join Branch with Company to get company name
    result = db.session.query(Branch, Company).join(Company, Branch.company_id == Company.id).filter(Branch.id == branch_id).first()

    if not result:
        return jsonify({"success": False, "message": "Branch not found"}), 404
    
    b, c = result
    data = {
        "id": b.id,
        "company_id": b.company_id,
        "branch_name": b.branch_name,
        "company_name": c.company_name,
        "address": b.address,
        "latitude": b.latitude,
        "longitude": b.longitude,
        "status": b.status
    }
    
    return jsonify({"success": True, "data": data}), 200


@company_bp.route("/branches/<int:branch_id>", methods=["PUT"])
@jwt_required
def update_branch(branch_id):
    guard = require_super_admin()
    if guard: return guard

    if not Branch:
        return jsonify({"success": False, "message": "Branch model not found"}), 500

    b = Branch.query.get(branch_id)
    if not b:
        return jsonify({"success": False, "message": "Branch not found"}), 404

    data = request.get_json(silent=True) or {}

    if "branch_name" in data:
        new_name = (data["branch_name"] or "").strip()
        if not new_name:
            return jsonify({"success": False, "message": "Branch name cannot be empty"}), 400
        b.branch_name = new_name

    if "address" in data: b.address = data["address"]
    if "latitude" in data: b.latitude = data["latitude"]
    if "longitude" in data: b.longitude = data["longitude"]
    if "status" in data: b.status = data["status"]

    db.session.commit()
    return jsonify({"success": True, "message": "Branch updated successfully"}), 200


@company_bp.route("/branches/<int:branch_id>", methods=["DELETE"])
@jwt_required
def delete_branch(branch_id):
    guard = require_super_admin()
    if guard: return guard

    if not Branch:
        return jsonify({"success": False, "message": "Branch model not found"}), 500

    b = Branch.query.get(branch_id)
    if not b:
        return jsonify({"success": False, "message": "Branch not found"}), 404

    try:
        db.session.delete(b)
        db.session.commit()
        return jsonify({"success": True, "message": "Branch deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error on deletion", "error": str(e)}), 500


@company_bp.route("/branches/<int:branch_id>/toggle-status", methods=["PUT"])
@jwt_required
def toggle_branch_status(branch_id):
    guard = require_super_admin()
    if guard: return guard

    if not Branch: return jsonify({"success": False, "message": "Branch model not found"}), 500

    b = Branch.query.get(branch_id)
    if not b: return jsonify({"success": False, "message": "Branch not found"}), 404

    current = (b.status or "Active").upper()
    b.status = "Inactive" if current == "ACTIVE" else "Active"
    
    db.session.commit()
    return jsonify({"success": True, "message": f"Branch status changed to {b.status}", "status": b.status}), 200


@company_bp.route("/branches/map", methods=["GET"])
@jwt_required
def get_branch_map():
    guard = require_super_admin()
    if guard: return guard

    if not Branch: return jsonify({"success": False, "message": "Branch model not found"}), 500

    # Only branches with valid lat/lng
    query = db.session.query(Branch, Company).join(Company, Branch.company_id == Company.id)
    query = query.filter(Branch.latitude != None, Branch.longitude != None)

    # Optional filter: ?status=Active
    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter(Branch.status == status_filter)

    results = query.all()
    pins = []
    for b, c in results:
        pins.append({
            "branch_id": b.id,
            "branch_name": b.branch_name,
            "company_name": c.company_name,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "status": b.status
        })

    return jsonify({"success": True, "data": pins}), 200


# ----------------------------
# 2) LIST COMPANIES
# GET /api/superadmin/companies
# ----------------------------
@company_bp.route("/companies", methods=["GET"])
@jwt_required
def list_companies():
    guard = require_super_admin()
    if guard:
        return guard

    # Debug: Check if the frontend is sending the token for the list request
    print("AUTH HEADER (list_companies):", request.headers.get("Authorization"))

    companies = Company.query.order_by(Company.id.desc()).all()

    data = []
    for c in companies:
        data.append({
            "id": c.id,
            "name": c.company_name,
            "company_code": c.company_code,
            "email": c.email,
            "address": c.address,
            "status": getattr(c, 'status', 'Active')
        })

    return jsonify({
        "success": True,
        "data": data
    }), 200


# ----------------------------
# 3) GET COMPANY
# GET /api/superadmin/companies/<id>
# ----------------------------
@company_bp.route("/companies/<int:company_id>", methods=["GET"])
@jwt_required
def get_company(company_id):
    guard = require_super_admin()
    if guard:
        return guard

    c = Company.query.get(company_id)
    if not c:
        return jsonify({"success": False, "message": "Company not found"}), 404

    return jsonify({
        "success": True,
        "data": {
            "id": c.id,
            "company_name": c.company_name,
            "company_code": c.company_code,
            "subdomain": c.subdomain,
            "industry": c.industry,
            "company_size": c.company_size,
            "country": c.country,
            "state": c.state,
            "city_branch": c.city_branch,
            "timezone": c.timezone,
            "address": c.address,
            "phone": c.phone,
            "email": c.email,
        }
    }), 200


# ----------------------------
# 4) UPDATE COMPANY
# PUT /api/superadmin/companies/<id>
# ----------------------------
@company_bp.route("/companies/<int:company_id>", methods=["PUT"])
@jwt_required
def update_company(company_id):
    guard = require_super_admin()
    if guard:
        return guard

    c = Company.query.get(company_id)
    if not c:
        return jsonify({"success": False, "message": "Company not found"}), 404

    data = request.get_json(silent=True) or {}

    # Allow updating these fields
    allowed = [
        "company_name", "company_code", "industry", "company_size",
        "country", "state", "city_branch", "timezone",
        "address", "phone", "email"
    ]
    for field in allowed:
        if field in data:
            setattr(c, field, data[field])

    # If frontend sends company_Id, map it
    if "company_Id" in data:
        c.company_code = (data.get("company_Id") or "").strip().upper()

    # subdomain update is optional (only if you want)
    if "subdomain" in data:
        sub = (data.get("subdomain") or "").strip().lower()
        if sub and Company.query.filter(Company.subdomain == sub, Company.id != c.id).first():
            return jsonify({"success": False, "message": "subdomain already exists"}), 400
        c.subdomain = sub

    db.session.commit()
    return jsonify({"success": True, "message": "Company updated successfully"}), 200


# ----------------------------
# DELETE COMPANY
# DELETE /api/superadmin/companies/<id>
# ----------------------------
@company_bp.route("/companies/<int:company_id>", methods=["DELETE"])
@jwt_required
def delete_company(company_id):
    guard = require_super_admin()
    if guard:
        return guard

    c = Company.query.get(company_id)
    if not c:
        return jsonify({"success": False, "message": "Company not found"}), 404

    try:
        db.session.delete(c)
        db.session.commit()
        return jsonify({"success": True, "message": "Company deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error", "error": str(e)}), 500


# ----------------------------
# 5) ADD USERS LATER (Option B)
# POST /api/superadmin/companies/<id>/users
# ----------------------------
@company_bp.route("/companies/<int:company_id>/users", methods=["POST"])
@jwt_required
def add_users_to_company(company_id):
    # RESTRICTION: Only HR can perform CRUD on employees.
    # Super Admin, Admin, Manager are NOT allowed.
    guard = require_hr_access()
    if guard:
        return guard

    c = Company.query.get(company_id)
    if not c:
        return jsonify({"success": False, "message": "Company not found"}), 404

    # Ensure HR is adding to their own company
    user = getattr(g, "user", None)
    if user.company_id != company_id:
        return jsonify({"success": False, "message": "Forbidden: You can only manage your own company employees"}), 403

    data = request.get_json(silent=True) or {}
    users_payload = data.get("users") or []

    if not isinstance(users_payload, list) or len(users_payload) == 0:
        return jsonify({"success": False, "message": "users must be a non-empty list"}), 400

    created_users = []
    failed_users = []

    try:
        for u in users_payload:
            email = (u.get("email") or "").strip()
            role = (u.get("role") or "").strip()
            name = (u.get("name") or "").strip()
            res, _ = create_user_and_email(c.id, email, role, name)
            if res["ok"]:
                created_users.append(res)
            else:
                failed_users.append(res)

        if failed_users:
            db.session.rollback()
            return jsonify({"success": False, "message": "Some users failed", "errors": failed_users}), 400

        db.session.commit()
        return jsonify({"success": True, "message": "Users created successfully", "data": created_users}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error", "error": str(e)}), 500
