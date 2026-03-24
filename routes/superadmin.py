from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash
import jwt
from config import Config
import secrets
import string
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from models.department import Department
from models.branch import Branch
from models.attendance import Attendance
from leave.models import LeaveRequest
from utils.decorators import token_required, role_required
from utils.email_utils import send_login_credentials, send_account_created_alert
import jwt
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
# Redundant create_company removed (handled by company.py)


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
        "company_id", "full_name",
        "company_email", "password", "confirm_password"
    ]
    
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    # CTC is optional now
    ctc_val = 0.0
    if data.get("ctc"):
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
            department=data.get("department") or "N/A",
            designation=data.get("designation") or "N/A",
            pay_grade=data.get("pay_grade") or "N/A",
            ctc=float(data.get("ctc") or 0.0),
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

        # Generate a reset token for the email link
        reset_token = jwt.encode(
            {
                'user_id': new_admin.id,
                'type': 'password_reset',
                'exp': datetime.utcnow() + timedelta(minutes=60)
            },
            current_app.config['SECRET_KEY'],
            algorithm="HS256"
        )

        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        created_by = "Super Admin"

        # Construct reset URL with token and email
        # Generate OTP as a fallback
        otp = new_admin.generate_otp()
        reset_url = f"{login_url.replace('/login', '/reset-password')}?token={reset_token}&email={company_email}&otp={otp}"
        send_account_created_alert(personal_email, company.company_name, created_by)

        # Mail 2: Login Credentials
        email_sent = send_login_credentials(
            personal_email=personal_email,
            company_email=company_email,
            company_name=company.company_name,
            web_address=web_address,
            reset_url=reset_url,
            created_by=created_by,
            full_name=data.get("full_name") or "Admin"
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
        "company_id", "full_name",
        "company_email"
    ]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    # CTC is optional now
    ctc_val = 0.0
    if data.get("ctc"):
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
    role = (data.get("role") or data.get("employee_type") or "EMPLOYEE").strip().upper()

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
            full_name=data.get("full_name") or data.get("name"),
            personal_email=data.get("personal_email"),
            company_email=data.get("company_email"),
            phone_number=data.get("phone_number") or data.get("phone"),
            department=data.get("department") or "N/A",
            designation=data.get("designation") or "N/A",
            pay_grade=data.get("pay_grade") or "N/A",
            ctc=float(data.get("ctc") or 0.0),
            employment_type=data.get("employment_type"),
            gender=data.get("gender"),
            date_of_birth=parse_date(data.get("date_of_birth")),
            date_of_joining=parse_date(data.get("date_of_joining") or data.get("joining_date")),
            manager_id=data.get("manager_id"),
        )
        db.session.add(emp)
        # Sync requested: employees.company_email ↔ users.email
        new_user.email = emp.company_email
        db.session.commit()

        # Generate a reset token for the email link
        reset_token = jwt.encode(
            {
                'user_id': new_user.id,
                'type': 'password_reset',
                'exp': datetime.utcnow() + timedelta(minutes=60)
            },
            current_app.config['SECRET_KEY'],
            algorithm="HS256"
        )

        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        
        # Construct reset URL with token and email
        # Generate OTP as a fallback
        otp = new_user.generate_otp()
        reset_url = f"{login_url.replace('/login', '/reset-password')}?token={reset_token}&email={company_email}&otp={otp}"
        
        email_sent = send_login_credentials(
            personal_email=personal_email,
            company_email=company_email,
            company_name=company.company_name,
            web_address=web_address,
            reset_url=login_url.replace("/login", "/reset-password"),
            created_by="Super Admin",
            full_name=data.get("full_name") or data.get("name") or "User"
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
            company_name=company.company_name,
            web_address=web_address,
            reset_url=login_url.replace("/login", "/reset-password"),
            created_by="Super Admin",
            full_name=name or "User"
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
# Redundant companies route removed (handled by company.py)


# POST /api/superadmin/companies/<company_id>/users
# Option B: Add users to existing company
# Redundant users route removed (handled by company.py)


# ======================================================
# ✅ 5) DASHBOARD STATS
# GET /api/superadmin/dashboard-stats
# ======================================================
@superadmin_bp.route("/dashboard-stats", methods=["GET"])
@token_required
@role_required(["SUPER_ADMIN"])
def get_dashboard_stats():
    try:
        total_companies = Company.query.count()
        total_branches = Branch.query.count()
        total_admins = User.query.filter_by(role="ADMIN").count()
        total_hrs = User.query.filter_by(role="HR").count()
        total_managers = User.query.filter_by(role="MANAGER").count()
        total_employees = Employee.query.count()

        # Department distribution
        departments = db.session.query(
            Employee.department, func.count(Employee.id)
        ).group_by(Employee.department).all()

        colors = ['#3b82f6', '#ec4899', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16']
        dept_data = []
        for i, (dept_name, count) in enumerate(departments):
            if dept_name:
                dept_data.append({
                    "label": dept_name,
                    "value": count,
                    "color": colors[i % len(colors)]
                })

        # Attendance summary (for today)
        today = date.today()
        attendance_counts = db.session.query(
            Attendance.status, func.count(Attendance.attendance_id)
        ).filter(Attendance.attendance_date == today).group_by(Attendance.status).all()
        
        att_dict = {status: count for status, count in attendance_counts}
        # If total_employees > sum of logged states, maybe calculate 'Not Marked' 
        # but the prompt wants to map the existing 5 UI elements
        attendance_summary = [
            {"label": "Present", "value": att_dict.get("Present", 0), "color": "#10b981"},
            {"label": "Absent", "value": att_dict.get("Absent", 0), "color": "#ef4444"},
            {"label": "WFH", "value": att_dict.get("WFH", 0), "color": "#3b82f6"},
            {"label": "Leave", "value": att_dict.get("Leave", 0) + att_dict.get("Half Day", 0), "color": "#f59e0b"},
            {"label": "WeekOff", "value": att_dict.get("WeekOff", 0), "color": "#6b7280"}
        ]

        # Growth trend (Employee joins per month for the current year)
        current_year = today.year
        employees = db.session.query(Employee.date_of_joining).filter(
            func.extract('year', Employee.date_of_joining) == current_year
        ).all()
        
        monthly_counts = [0] * 12
        for emp in employees:
            if emp.date_of_joining:
                monthly_counts[emp.date_of_joining.month - 1] += 1
                
        # Calculate cumulative growth for the year
        revenue_trend = []
        cumulative = 0
        for count in monthly_counts:
            cumulative += count
            revenue_trend.append(cumulative)

        # Pending Requests (from LeaveRequest)
        pending_leaves = LeaveRequest.query.filter(
            LeaveRequest.status.in_(['Pending', 'Pending Approval'])
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()

        pending_requests = []
        req_colors = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#3b82f6']
        for i, req in enumerate(pending_leaves):
            emp_name = req.employee.full_name if req.employee and req.employee.full_name else "Unknown"
            initials = "".join([n[0] for n in emp_name.split() if n])[:2].upper() if emp_name else "U"
            pending_requests.append({
                "id": req.id,
                "name": emp_name,
                "initials": initials,
                "type": "Leave",
                "color": req_colors[i % len(req_colors)]
            })

        return jsonify({
            "success": True,
            "data": {
                "stats": {
                    "total_companies": total_companies,
                    "total_branches": total_branches,
                    "total_admins": total_admins,
                    "total_hrs": total_hrs,
                    "total_managers": total_managers,
                    "total_employees": total_employees
                },
                "departmentData": dept_data,
                "attendanceSummary": attendance_summary,
                "revenueTrend": revenue_trend,
                "pendingRequests": pending_requests
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Failed to fetch dashboard stats", "error": str(e)}), 500

# ======================================================
# ✅ 6) DELETE EMPLOYEE (Soft Delete by default)
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
