from flask import Blueprint, request, jsonify, g
from datetime import datetime, date
import csv
import io

from models import db
from models.attendance import Attendance, AttendanceRegularization
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, role_required

attendance_bp = Blueprint("attendance", __name__)

ALLOWED_MANAGE_ROLES = ["SUPER_ADMIN", "ADMIN", "HR", "MANAGER"]

def has_attendance_permission():
    """Checks if the current user has permission to manage attendance."""
    if g.user.role in ['SUPER_ADMIN', 'ADMIN']:
        return True
    return g.user.has_permission('MANAGE_ATTENDANCE')


# -----------------------------
# Helpers
# -----------------------------
def _parse_date(value: str) -> date:
    """
    Accepts:
      - YYYY-MM-DD
      - DD/MM/YYYY
      - MM/DD/YYYY (if you want; can remove)
    """
    if not value:
        raise ValueError("date is required")

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {value}")


def _parse_time(value: str, base_date: date) -> datetime:
    """
    Accepts:
      - HH:MM
      - HH:MM:SS
      - 09:45
      - 19:34
    """
    if not value:
        return None

    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p", "%I:%M%p"):
        try:
            t = datetime.strptime(value, fmt).time()
            return datetime.combine(base_date, t)
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: {value}")


def _format_logged_time(total_minutes: int) -> str:
    hrs = total_minutes // 60
    mins = total_minutes % 60
    if hrs > 0 and mins > 0:
        return f"{hrs} hrs {mins} mins"
    if hrs > 0:
        return f"{hrs} hrs"
    return f"{mins} mins"


def _calc_total_minutes(in_dt, out_dt):
    if not in_dt or not out_dt or out_dt < in_dt:
        return 0
    return int((out_dt - in_dt).total_seconds() / 60)

def _get_employee_in_company(employee_id: int) -> Employee:
    emp = Employee.query.get(employee_id)
    if not emp or emp.company_id != g.user.company_id:
        return None
    return emp


def _upsert_attendance(company_id: int, employee_id: int, att_date: date, payload: dict, capture_method: str):
    row = Attendance.query.filter_by(
        company_id=company_id,
        employee_id=employee_id,
        attendance_date=att_date
    ).first()

    is_new = False
    if not row:
        row = Attendance(company_id=company_id, employee_id=employee_id, attendance_date=att_date)
        row.year = att_date.year
        row.month = att_date.month
        row.created_by = getattr(g.user, "id", None)
        db.session.add(row)
        is_new = True

    # 1. Update status if provided
    if payload.get("status"):
        row.status = payload["status"]

    if "remarks" in payload:
        row.remarks = payload["remarks"]

    # 2. If Absent, CLEAR times. Otherwise, update times if provided.
    if row.status == "Absent":
        row.punch_in_time = None
        row.punch_out_time = None
        row.total_minutes = 0
    else:
        if payload.get("login_at") is not None:
            row.punch_in_time = payload["login_at"]
        if payload.get("logout_at") is not None:
            row.punch_out_time = payload["logout_at"]
        
        row.total_minutes = _calc_total_minutes(row.punch_in_time, row.punch_out_time)

    row.capture_method = capture_method

    row.updated_by = getattr(g.user, "id", None)

    return row, is_new


# -----------------------------
# 1) List Attendance (Table)
# -----------------------------
@attendance_bp.route("", methods=["GET"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def list_attendance():
    """
    Filters used by your UI:
      - role (Admin/HR/Manager/Employee/Accountant)
      - department
      - day=all/today
      - month (1-12) optional
      - from_date, to_date
      - search (name/email)
    """
    role = request.args.get("role")          # Role dropdown
    department = request.args.get("department")
    day = (request.args.get("day") or "all").lower()  # all / today
    month = request.args.get("month")        # 1..12
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    search = (request.args.get("search") or "").strip().lower()

    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    q = Attendance.query

    # Filter by company (unless Super Admin)
    if g.user.role != 'SUPER_ADMIN':
        q = q.filter(Attendance.company_id == g.user.company_id)

    # Day filter
    if day == "today":
        q = q.filter(Attendance.attendance_date == date.today())

    # Date range filter
    if from_date:
        q = q.filter(Attendance.attendance_date >= _parse_date(from_date))
    if to_date:
        q = q.filter(Attendance.attendance_date <= _parse_date(to_date))

    # Month filter (optional)
    if month:
        try:
            m = int(month)
            q = q.filter(Attendance.month == m)
        except:
            pass

    # Join with employee + user for role/department/search
    q = q.join(Employee, Employee.id == Attendance.employee_id) \
         .outerjoin(User, User.id == Employee.user_id)

    if g.user.role != 'SUPER_ADMIN':
        q = q.filter(Employee.company_id == g.user.company_id)

    if department:
        q = q.filter(Employee.department == department)

    if role:
        q = q.filter(User.role == role)

    if search:
        q = q.filter(
            db.or_(
                db.func.lower(Employee.first_name).like(f"%{search}%"),
                db.func.lower(Employee.last_name).like(f"%{search}%"),
                db.func.lower(User.email).like(f"%{search}%"),
                db.func.lower(getattr(Employee, "employee_id", "")).like(f"%{search}%")
            )
        )

    rows = q.order_by(Attendance.attendance_date.desc()).limit(500).all()

    output = []
    for r in rows:
        emp = Employee.query.get(r.employee_id)
        user = User.query.get(emp.user_id) if emp else None

        output.append({
            "id": r.attendance_id,
            "attendance_id": r.attendance_id,
            "employee_id": emp.employee_id if emp else "",
            "name": f"{emp.first_name} {emp.last_name}" if emp else "",
            "role": user.role if user else None,
            "department": emp.department if emp else None,
            "status": r.status,
            "remarks": getattr(r, "remarks", ""),
            "logged_time": _format_logged_time(r.total_minutes),
            "login_at": r.punch_in_time.strftime("%I:%M %p") if r.punch_in_time else None,
            "logout_at": r.punch_out_time.strftime("%I:%M %p") if r.punch_out_time else None,
            "date": r.attendance_date.strftime("%d/%m/%Y"),
        })

    return jsonify({"attendance": output}), 200


# -----------------------------
# 2) Manual Attendance (Create/Upsert)
# -----------------------------
@attendance_bp.route("", methods=["POST"])
@attendance_bp.route("/manual", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def manual_attendance():
    """
    Manual button action (UPSERT):
      Required: employee_id, date
      Optional: status, login_at, logout_at
    """
    data = request.get_json() or {}

    employee_id = data.get("employee_id")
    att_date = data.get("date")  # "2025-10-02" or "02/10/2025"
    status = data.get("status")  # Don't default to "Present" here, let upsert handle it
    remarks = data.get("remarks", "")

    if not employee_id or not att_date:
        return jsonify({"message": "employee_id and date are required"}), 400

    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    # Handle Super Admin lookup (find employee across any company)
    # 1. Try by Employee Code (string)
    query = Employee.query.filter_by(employee_id=str(employee_id))
    if g.user.role != 'SUPER_ADMIN':
        query = query.filter_by(company_id=g.user.company_id)
    emp = query.first()
    
    # 2. If not found, try by Primary Key (ID)
    if not emp and str(employee_id).isdigit():
        emp = Employee.query.filter_by(id=int(employee_id)).first()
        if emp and g.user.role != 'SUPER_ADMIN' and emp.company_id != g.user.company_id:
            emp = None

    if not emp:
        return jsonify({"message": "Employee not found"}), 404

    # Enforce Rule: Employees cannot mark their own attendance (even HR/Managers with permission)
    if emp.user_id == g.user.id and g.user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({"message": "You cannot mark your own attendance manually"}), 403

    d = _parse_date(att_date)

    login_at = None
    logout_at = None

    # If absent -> times should be empty (allowed)
    raw_login = data.get("login_at") or data.get("in_time")
    if raw_login:
        login_at = _parse_time(raw_login, d)

    raw_logout = data.get("logout_at") or data.get("out_time")
    if raw_logout:
        logout_at = _parse_time(raw_logout, d)

    payload = {
        "status": status,
        "login_at": login_at,
        "logout_at": logout_at,
        "remarks": remarks
    }

    row, is_new = _upsert_attendance(emp.company_id, emp.id, d, payload, capture_method="Manual")
    db.session.commit()

    return jsonify({
        "message": "Attendance saved successfully",
        "action": "inserted" if is_new else "updated",
        "attendance_id": row.attendance_id,
        "id": row.attendance_id
    }), 200


# -----------------------------
# 3) Update Attendance (Edit icon)
# -----------------------------
@attendance_bp.route("/<int:attendance_id>", methods=["PUT"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def update_attendance(attendance_id):
    data = request.get_json() or {}
    row = Attendance.query.get(attendance_id)

    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    if not row:
        return jsonify({"message": "Attendance not found"}), 404

    # Allow Super Admin or Company Admin
    if g.user.role != 'SUPER_ADMIN' and row.company_id != g.user.company_id:
        return jsonify({"message": "Attendance not found"}), 404

    # Support aliases for time fields (in_time -> login_at)
    if "in_time" in data and "login_at" not in data:
        data["login_at"] = data["in_time"]
    if "out_time" in data and "logout_at" not in data:
        data["logout_at"] = data["out_time"]

    # Update values
    if "status" in data:
        row.status = data["status"] or row.status

    if "remarks" in data:
        row.remarks = data["remarks"]

    if "login_at" in data:
        if data["login_at"]:
            row.punch_in_time = _parse_time(data["login_at"], row.attendance_date)
        else:
            row.punch_in_time = None

    if "logout_at" in data:
        if data["logout_at"]:
            row.punch_out_time = _parse_time(data["logout_at"], row.attendance_date)
        else:
            row.punch_out_time = None

    row.total_minutes = _calc_total_minutes(row.punch_in_time, row.punch_out_time)

    row.capture_method = "Manual"
    row.updated_by = getattr(g.user, "id", None)

    db.session.commit()
    return jsonify({"message": "Attendance updated successfully"}), 200


# -----------------------------
# 4) Delete Attendance (Delete icon)
# -----------------------------
@attendance_bp.route("/<int:attendance_id>", methods=["DELETE"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def delete_attendance(attendance_id):
    row = Attendance.query.get(attendance_id)
    if not row:
        return jsonify({"message": "Attendance not found"}), 404

    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    # Allow Super Admin or Company Admin
    if g.user.role != 'SUPER_ADMIN' and row.company_id != g.user.company_id:
        return jsonify({"message": "Attendance not found"}), 404

    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Attendance deleted successfully"}), 200


# -----------------------------
# 5) Import Attendance (CSV/XLSX) with UPSERT
# -----------------------------
# ---------- helpers for import ----------
def pick_uploaded_file():
    """
    Accept file from:
    - request.files['file']
    - request.files['any_other_key']
    """
    if not request.files:
        return None
    return request.files.get("file") or next(iter(request.files.values()), None)

def norm(s):
    return (s or "").strip()

def norm_key(s):
    return norm(s).lower().replace(" ", "_")

def parse_date_any(date_str):
    date_str = norm(date_str)
    if not date_str:
        return None
    # supports: 2025-10-02 , 02/10/2025 , 10/02/2025
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            pass
    return None

def parse_time_any(d, t):
    t = norm(t)
    if not t:
        return None
    # supports: 09:45 , 09:45:00
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            tm = datetime.strptime(t, fmt).time()
            return datetime(d.year, d.month, d.day, tm.hour, tm.minute, tm.second)
        except:
            pass
    return None

def pick(row, *keys):
    """Try multiple possible header names."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return ""

def normalize_status(s):
    s = norm(s).lower()
    if not s:
        return "Absent"
    # accept many variants
    if s in ["present", "p", "yes", "1"]:
        return "Present"
    if s in ["absent", "a", "no", "0"]:
        return "Absent"
    if s in ["halfday", "half_day", "half day", "hd"]:
        return "Half Day"
    if s in ["fullday", "full_day", "full day", "fd"]:
        return "Full Day"
    return s.title()

@attendance_bp.route("/import", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def import_attendance():
    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    uploaded = pick_uploaded_file()
    if not uploaded:
        return jsonify({"message": "No file found. Please send multipart/form-data with any file key."}), 400

    # read file content
    try:
        raw_bytes = uploaded.read()
        text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        return jsonify({"message": "Unable to read file", "error": str(e)}), 400

    # parse CSV
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return jsonify({"message": "Invalid CSV: header row missing"}), 400

    inserted = updated = failed = 0
    errors = []

    for idx, r in enumerate(reader, start=2):
        try:
            # normalize keys
            row = {norm_key(k): norm(v) for k, v in (r or {}).items()}

            # employee id can be employee_id / emp_id / employee / id etc
            emp_id_val = pick(row, "employee_id", "emp_id", "employee", "employeeid", "empid", "id")
            if not emp_id_val:
                failed += 1
                errors.append({"row": idx, "reason": "employee_id missing"})
                continue

            # Look up by string employee_id first (business key)
            query = Employee.query.filter_by(employee_id=emp_id_val)
            if g.user.role != 'SUPER_ADMIN':
                query = query.filter_by(company_id=g.user.company_id)
            emp = query.first()
            if not emp:
                failed += 1
                errors.append({"row": idx, "reason": f"Employee not found: {emp_id_val}"})
                continue

            # date can be date / attendance_date / att_date
            d_str = pick(row, "date", "attendance_date", "att_date", "day")
            d = parse_date_any(d_str)
            if not d:
                failed += 1
                errors.append({"row": idx, "reason": f"Invalid date: {d_str}"})
                continue

            # time columns can be login_at/logout_at OR in_time/out_time OR punch_in_time/punch_out_time
            login_str = pick(row, "login_at", "in_time", "punch_in_time", "punch_in", "login", "in")
            logout_str = pick(row, "logout_at", "out_time", "punch_out_time", "punch_out", "logout", "out")

            in_dt = parse_time_any(d, login_str)
            out_dt = parse_time_any(d, logout_str)

            status = normalize_status(pick(row, "status", "attendance", "att_status"))
            remarks = pick(row, "remarks", "remark", "note", "notes", "comment", "comments")

            # upsert attendance
            rec = Attendance.query.filter_by(employee_id=emp.id, date=d).first()
            if not rec:
                rec = Attendance(
                    company_id=emp.company_id,
                    employee_id=emp.id,
                    date=d,
                    year=d.year,
                    month=d.month,
                    marked_by="Import",
                    status="ABSENT"
                )
                db.session.add(rec)
                inserted += 1
            else:
                updated += 1
                rec.marked_by = "Import"

            rec.status = status
            rec.in_time = in_dt
            rec.out_time = out_dt
            
            minutes = _calc_total_minutes(in_dt, out_dt)
            rec.work_hours = round(minutes / 60.0, 2)
            rec.total_minutes = minutes

            if hasattr(rec, "remarks"):
                rec.remarks = remarks

        except Exception as e:
            failed += 1
            errors.append({"row": idx, "reason": str(e)})

    db.session.commit()
    return jsonify({
        "message": "Import completed",
        "inserted": inserted,
        "updated": updated,
        "failed": failed,
        "errors": errors
    }), 200


# -----------------------------
# 6) Employee view only (No create)
# -----------------------------
@attendance_bp.route("/me", methods=["GET"])
@token_required
@role_required(["EMPLOYEE", "ADMIN", "HR", "MANAGER", "SUPER_ADMIN"])
def my_attendance():
    """
    Employee can only view their own attendance.
    No punch in/out APIs here.
    """
    query = Employee.query.filter_by(user_id=g.user.id)
    if g.user.role != 'SUPER_ADMIN':
        query = query.filter_by(company_id=g.user.company_id)
    emp = query.first()
    if not emp:
        return jsonify({"message": "Employee profile not found"}), 404

    q = Attendance.query.filter_by(employee_id=emp.id)\
                        .order_by(Attendance.attendance_date.desc())\
                        .limit(180)

    output = []
    for r in q.all():
        output.append({
            "id": r.attendance_id,
            "status": r.status,
            "remarks": getattr(r, "remarks", ""),
            "logged_time": _format_logged_time(r.total_minutes),
            "login_at": r.punch_in_time.strftime("%I:%M %p") if r.punch_in_time else None,
            "logout_at": r.punch_out_time.strftime("%I:%M %p") if r.punch_out_time else None,
            "date": r.attendance_date.strftime("%d/%m/%Y"),
        })

    return jsonify({"attendance": output}), 200


# -----------------------------
# 7) Login / Logout APIs
# -----------------------------
@attendance_bp.route("/login", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def attendance_login():
    data = request.get_json()
    employee_id = data.get("employee_id")
    status = data.get("status", "Present")

    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: Employees cannot mark their own attendance"}), 403

    if not employee_id:
        return jsonify({"message": "employee_id required"}), 400

    # Build query to find employee, handling Super Admin case
    query = Employee.query.filter_by(employee_id=employee_id)
    if g.user.role != 'SUPER_ADMIN':
        query = query.filter_by(company_id=g.user.company_id)
    emp = query.first()

    if not emp:
        return jsonify({"message": "Employee not found"}), 404

    # Enforce Rule: Employees cannot mark their own attendance
    if emp.user_id == g.user.id and g.user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({"message": "You cannot mark your own attendance manually"}), 403

    today = date.today()

    attendance = Attendance.query.filter_by(
        employee_id=emp.id,
        attendance_date=today
    ).first()

    if attendance:
        return jsonify({"message": "Already logged in"}), 400

    punch_in_time = datetime.now()
    if status == "Absent":
        punch_in_time = None

    attendance = Attendance(
        employee_id=emp.id,
        company_id=emp.company_id,
        attendance_date=today,
        year=today.year,
        month=today.month,
        punch_in_time=punch_in_time,
        status=status,
        capture_method="Manual",
        created_by=g.user.id
    )

    db.session.add(attendance)
    db.session.commit()

    return jsonify({"message": "Login recorded"}), 201

@attendance_bp.route("/logout", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def attendance_logout():
    data = request.get_json()
    employee_id = data.get("employee_id")

    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: Employees cannot mark their own attendance"}), 403

    # Build query to find employee, handling Super Admin case
    query = Employee.query.filter_by(employee_id=employee_id)
    if g.user.role != 'SUPER_ADMIN':
        query = query.filter_by(company_id=g.user.company_id)
    emp = query.first()
    if not emp: return jsonify({"message": "Employee not found"}), 404

    # Enforce Rule: Employees cannot mark their own attendance
    if emp.user_id == g.user.id and g.user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({"message": "You cannot mark your own attendance manually"}), 403

    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()

    if not attendance: return jsonify({"message": "Login not found"}), 404
    if attendance.punch_out_time: return jsonify({"message": "Already logged out"}), 400

    attendance.punch_out_time = datetime.now()
    attendance.updated_by = g.user.id
    db.session.commit()

    return jsonify({"message": "Logout recorded"}), 200


# -----------------------------
# 8) Regularization (Correction)
# -----------------------------
@attendance_bp.route("/regularization/request", methods=["POST"])
@token_required
def create_regularization_request():
    data = request.get_json()
    
    # 1. Identify Employee
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({"message": "Employee profile not found"}), 404

    # 2. Validate Inputs
    att_date_str = data.get("attendance_date")
    if not att_date_str:
        return jsonify({"message": "attendance_date is required"}), 400
    
    try:
        d = _parse_date(att_date_str)
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    # 3. Parse Times (if provided)
    login_at = None
    logout_at = None
    if data.get("requested_login_at"):
        login_at = _parse_time(data["requested_login_at"], d)
    if data.get("requested_logout_at"):
        logout_at = _parse_time(data["requested_logout_at"], d)

    # 4. Create Request
    reg = AttendanceRegularization(
        company_id=emp.company_id,
        employee_id=emp.id,
        attendance_date=d,
        requested_status=data.get("requested_status"),
        requested_punch_in=login_at,
        requested_punch_out=logout_at,
        reason=data.get("reason"),
        status="PENDING"
    )
    
    db.session.add(reg)
    db.session.commit()

    return jsonify({
        "message": "Regularization request submitted",
        "request_id": reg.id,
        "status": "PENDING"
    }), 201

@attendance_bp.route("/regularization/my-requests", methods=["GET"])
@token_required
def my_regularization_requests():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({"message": "Employee profile not found"}), 404

    reqs = AttendanceRegularization.query.filter_by(employee_id=emp.id).order_by(AttendanceRegularization.created_at.desc()).all()
    
    output = []
    for r in reqs:
        # Fetch current status
        att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=r.attendance_date).first()
        current_status = att.status if att else "Absent"

        output.append({
            "request_id": r.id,
            "attendance_date": r.attendance_date.strftime("%Y-%m-%d"),
            "current_status": current_status,
            "requested_status": r.requested_status,
            "status": r.status,
            "reason": r.reason,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return jsonify({"requests": output}), 200

@attendance_bp.route("/regularization/pending", methods=["GET"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def pending_regularization_requests():
    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    q = AttendanceRegularization.query
    
    # Super Admin sees all, others see only their company
    if g.user.role != 'SUPER_ADMIN':
        q = q.filter_by(company_id=g.user.company_id)

    # Filters
    status = request.args.get("status", "PENDING")
    if status:
        q = q.filter_by(status=status)

    rows = q.order_by(AttendanceRegularization.created_at.desc()).all()
    
    output = []
    for r in rows:
        # Fetch current status
        att = Attendance.query.filter_by(employee_id=r.employee_id, attendance_date=r.attendance_date).first()
        current_status = att.status if att else "Absent"

        output.append({
            "request_id": r.id,
            "employee_id": r.employee.employee_id if r.employee else "",
            "employee_name": r.employee.full_name if r.employee else "Unknown",
            "attendance_date": r.attendance_date.strftime("%Y-%m-%d"),
            "current_status": current_status,
            "requested_status": r.requested_status,
            "requested_login_at": r.requested_punch_in.strftime("%I:%M %p") if r.requested_punch_in else None,
            "requested_logout_at": r.requested_punch_out.strftime("%I:%M %p") if r.requested_punch_out else None,
            "reason": r.reason,
            "status": r.status
        })
    return jsonify({"pending": output}), 200

@attendance_bp.route("/regularization/<int:request_id>/approve", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def approve_regularization(request_id):
    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    data = request.get_json() or {}
    req = AttendanceRegularization.query.get_or_404(request_id)
    
    if g.user.role != 'SUPER_ADMIN' and req.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403

    req.status = "APPROVED"
    req.approved_by = g.user.id
    req.approver_comment = data.get("approver_comment")

    # --- UPDATE ATTENDANCE ---
    att = Attendance.query.filter_by(employee_id=req.employee_id, attendance_date=req.attendance_date).first()
    if not att:
        att = Attendance(company_id=req.company_id, employee_id=req.employee_id, attendance_date=req.attendance_date, created_by=g.user.id)
        db.session.add(att)

    if req.requested_status: att.status = req.requested_status
    if req.requested_punch_in: att.punch_in_time = req.requested_punch_in
    if req.requested_punch_out: att.punch_out_time = req.requested_punch_out
    
    att.capture_method = "Regularization"
    att.updated_by = g.user.id
    
    db.session.commit()
    return jsonify({"message": "Request approved and attendance updated", "request_id": req.id, "attendance_action": "updated"}), 200

@attendance_bp.route("/regularization/<int:request_id>/reject", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def reject_regularization(request_id):
    if not has_attendance_permission():
        return jsonify({"message": "Permission denied: MANAGE_ATTENDANCE required"}), 403

    data = request.get_json() or {}
    req = AttendanceRegularization.query.get_or_404(request_id)

    if g.user.role != 'SUPER_ADMIN' and req.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403

    req.status = "REJECTED"
    req.approved_by = g.user.id
    req.approver_comment = data.get("approver_comment")
    
    db.session.commit()
    return jsonify({"message": "Request rejected", "request_id": req.id, "status": "REJECTED"}), 200