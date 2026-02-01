from flask import Blueprint, request, jsonify, g, make_response, send_file, current_app
from datetime import datetime, date
import csv
import io
import os
import openpyxl
from werkzeug.utils import secure_filename

from models import db
from models.attendance import Attendance
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, role_required

attendance_bp = Blueprint("attendance", __name__)

ALLOWED_MANAGE_ROLES = ["SUPER_ADMIN", "ADMIN", "HR", "MANAGER"]


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
    for fmt in ("%H:%M", "%H:%M:%S"):
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


def _get_employee_in_company(identifier) -> Employee:
    # 1. Try Primary Key (if numeric)
    if str(identifier).isdigit():
        emp = Employee.query.get(int(identifier))
        if emp and emp.company_id == g.user.company_id:
            return emp

    # 2. Try Employee Code (string)
    emp = Employee.query.filter_by(employee_id=str(identifier), company_id=g.user.company_id).first()
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
        row.created_by = getattr(g.user, "id", None)
        db.session.add(row)
        is_new = True

    # Update allowed fields
    row.status = payload.get("status", row.status) or row.status
    row.capture_method = capture_method

    login_at = payload.get("login_at")
    logout_at = payload.get("logout_at")

    if login_at is not None:
        row.punch_in_time = login_at
    if logout_at is not None:
        row.punch_out_time = logout_at

    row.updated_by = getattr(g.user, "id", None)

    # Auto calculate logged time
    row.recalc_total_minutes()

    return row, is_new


# -----------------------------
# 1) List Attendance (Table)
# -----------------------------
@attendance_bp.route("", methods=["GET"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def list_attendance():
    """
    GET /api/attendance
    Filters used by your UI:
      - role (Admin/HR/Manager/Employee/Accountant)
      - department
      - day=all/today
      - month (1-12) optional
      - from_date, to_date
      - search (name/email)
    """
    company_id = g.user.company_id

    role = request.args.get("role")          # Role dropdown
    department = request.args.get("department")
    day = (request.args.get("day") or "all").lower()  # all / today
    month = request.args.get("month")        # 1..12
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    search = (request.args.get("search") or "").strip().lower()

    q = Attendance.query.filter_by(company_id=company_id)

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
            q = q.filter(db.extract("month", Attendance.attendance_date) == m)
        except:
            pass

    # Join with employee + user for role/department/search
    q = q.join(Employee, Employee.id == Attendance.employee_id)\
         .join(User, User.id == Employee.user_id)\
         .filter(Employee.company_id == company_id)

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
            "attendance_id": r.attendance_id,
            "employee_id": r.employee_id,
            "name": f"{emp.first_name} {emp.last_name}" if emp else "",
            "role": user.role if user else None,
            "department": emp.department if emp else None,
            "status": r.status,
            "logged_time": _format_logged_time(r.total_minutes),
            "login_at": r.punch_in_time.strftime("%H:%M") if r.punch_in_time else None,
            "logout_at": r.punch_out_time.strftime("%H:%M") if r.punch_out_time else None,
            "date": r.attendance_date.strftime("%d/%m/%Y"),
        })

    return jsonify({"attendance": output}), 200


# -----------------------------
# 7) Download Import Template
# -----------------------------
@attendance_bp.route("/import-template", methods=["GET"])
@token_required
def download_template():
    """
    Download CSV or XLSX template for attendance import.
    Query param: format=csv (default) or format=xlsx
    """
    fmt = request.args.get("format", "csv").lower()

    # Data from user requirement
    headers = ["employee_id", "date", "status", "login_at", "logout_at"]
    sample_data = [
        [1, "2023-10-25", "Present", "09:00", "18:00"],
        [2, "2023-10-25", "Absent", "", ""],
        [3, "2023-10-25", "Present", "09:15", "18:10"]
    ]

    if fmt == "xlsx":
        try:
            from io import BytesIO
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
            for row in sample_data:
                ws.append(row)
            out = BytesIO()
            wb.save(out)
            out.seek(0)
            return send_file(out, download_name="attendance_import_template.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except ImportError:
            return jsonify({"message": "openpyxl not installed"}), 500

    # CSV Default
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    cw.writerows(sample_data)
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=attendance_import_template.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# -----------------------------
# 2) Manual Attendance (Create/Upsert)
# -----------------------------
@attendance_bp.route("/manual", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def manual_attendance():
    """
    POST /api/attendance/manual
    Manual button action (UPSERT):
      Required: employee_id, date
      Optional: status, login_at, logout_at
    """
    data = request.get_json() or {}

    employee_id = data.get("employee_id")
    att_date = data.get("date")  # "2025-10-02" or "02/10/2025"
    status = data.get("status", "Present")

    if not employee_id or not att_date:
        return jsonify({"message": "employee_id and date are required"}), 400

    emp = _get_employee_in_company(employee_id)
    if not emp:
        return jsonify({"message": "Employee not found"}), 404

    d = _parse_date(att_date)

    login_at = None
    logout_at = None

    # If absent -> times should be empty (allowed)
    if data.get("login_at"):
        login_at = _parse_time(data["login_at"], d)
    if data.get("logout_at"):
        logout_at = _parse_time(data["logout_at"], d)

    payload = {
        "status": status,
        "login_at": login_at,
        "logout_at": logout_at
    }

    row, is_new = _upsert_attendance(g.user.company_id, emp.id, d, payload, capture_method="Manual")
    db.session.commit()

    return jsonify({
        "message": "Attendance saved successfully",
        "action": "inserted" if is_new else "updated",
        "attendance_id": row.attendance_id
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

    if not row or row.company_id != g.user.company_id:
        return jsonify({"message": "Attendance not found"}), 404

    # Update values
    if "status" in data:
        row.status = data["status"] or row.status

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

    row.capture_method = "Manual"
    row.updated_by = getattr(g.user, "id", None)
    row.recalc_total_minutes()

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
    if not row or row.company_id != g.user.company_id:
        return jsonify({"message": "Attendance not found"}), 404

    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Attendance deleted successfully"}), 200


# -----------------------------
# 5) Import Attendance (CSV/XLSX) with UPSERT
# -----------------------------
@attendance_bp.route("/import", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def import_attendance():
    """
    Supports:
      - CSV
      - XLSX (optional)
    Columns accepted:
      employee_id (required) OR employee_code (if you store it in Employee.employee_id string)
      date (required)
      status (Present/Absent)
      login_at (HH:MM)
      logout_at (HH:MM)

    UPSERT:
      company_id + employee_id + date exists => update
    """
    # Try to get the file from 'file' key, or just take the first file uploaded
    f = request.files.get("file")
    if not f and request.files:
        f = next(iter(request.files.values()))

    if not f:
        return jsonify({"message": "File is required (multipart/form-data). Key should be 'file'."}), 400

    filename = (f.filename or "").lower()

    # Save file to disk
    upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "attendance_imports")
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, secure_filename(f.filename))
    f.save(save_path)

    inserted = 0
    updated = 0
    errors = []

    company_id = g.user.company_id

    def handle_row(raw, row_no):
        nonlocal inserted, updated, errors

        try:
            # employee_id required
            emp_id = raw.get("employee_id")
            if not emp_id:
                raise ValueError("employee_id is required")

            emp = _get_employee_in_company(emp_id)
            if not emp:
                raise ValueError(f"Employee not found or not in company (employee_id={emp_id})")

            d = _parse_date(raw.get("date", ""))

            status = raw.get("status", "Present") or "Present"

            login_at = _parse_time(raw.get("login_at", ""), d) if raw.get("login_at") else None
            logout_at = _parse_time(raw.get("logout_at", ""), d) if raw.get("logout_at") else None

            payload = {"status": status, "login_at": login_at, "logout_at": logout_at}

            row, is_new = _upsert_attendance(company_id, emp.id, d, payload, capture_method="Import")
            if is_new:
                inserted += 1
            else:
                updated += 1

        except Exception as e:
            errors.append({"row": row_no, "error": str(e), "data": raw})

    # CSV
    if filename.endswith(".csv"):
        # Read from saved file
        with open(save_path, "r", encoding="utf-8", errors="ignore") as f_obj:
            reader = csv.DictReader(f_obj)

            for idx, r in enumerate(reader, start=2):  # 2 => header is row 1
                # normalize keys
                row = { (k or "").strip().lower(): (v or "").strip() for k, v in r.items() }
                handle_row(row, idx)

        db.session.commit()
        return jsonify({
            "message": "Import completed",
            "inserted": inserted,
            "updated": updated,
            "errors_count": len(errors),
            "errors": errors[:50]  # return first 50 only
        }), 200

    # XLSX (optional)
    if filename.endswith(".xlsx"):

        wb = openpyxl.load_workbook(save_path, data_only=True)
        ws = wb.active

        headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]

        for i in range(2, ws.max_row + 1):
            row_obj = {}
            for j, h in enumerate(headers, start=1):
                val = ws.cell(row=i, column=j).value
                row_obj[h] = str(val).strip() if val is not None else ""

            handle_row(row_obj, i)

        db.session.commit()
        return jsonify({
            "message": "Import completed",
            "inserted": inserted,
            "updated": updated,
            "errors_count": len(errors),
            "errors": errors[:50]
        }), 200

    return jsonify({"message": "Unsupported file type. Use .csv or .xlsx"}), 400


# -----------------------------
# 6) Employee view only (No create)
# -----------------------------
@attendance_bp.route("/me", methods=["GET"])
@token_required
@role_required(["EMPLOYEE", "ACCOUNTANT"])
def my_attendance():
    """
    Employee can only view their own attendance.
    No punch in/out APIs here.
    """
    emp = Employee.query.filter_by(user_id=g.user.id, company_id=g.user.company_id).first()
    if not emp:
        return jsonify({"message": "Employee profile not found"}), 404

    q = Attendance.query.filter_by(company_id=g.user.company_id, employee_id=emp.id)\
                        .order_by(Attendance.attendance_date.desc())\
                        .limit(180)

    output = []
    for r in q.all():
        output.append({
            "status": r.status,
            "logged_time": _format_logged_time(r.total_minutes),
            "login_at": r.punch_in_time.strftime("%H:%M") if r.punch_in_time else None,
            "logout_at": r.punch_out_time.strftime("%H:%M") if r.punch_out_time else None,
            "date": r.attendance_date.strftime("%d/%m/%Y"),
        })

    return jsonify({"attendance": output}), 200