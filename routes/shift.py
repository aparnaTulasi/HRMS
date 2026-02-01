from flask import Blueprint, request, jsonify, g
from datetime import datetime
from models import db
from models.shift import Shift, ShiftAssignment
from models.employee import Employee
from utils.decorators import token_required, role_required

shift_bp = Blueprint("shift", __name__)

MANAGE_ROLES = ["SUPER_ADMIN", "ADMIN", "HR"]

def _parse_time(t: str):
    # Accept "09:30" or "09:30:00"
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(t, fmt).time()
        except ValueError:
            pass
    raise ValueError("Invalid time format. Use HH:MM (example: 09:30)")

def _parse_date(d: str):
    # Accept "YYYY-MM-DD" or "DD/MM/YYYY"
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except ValueError:
            pass
    raise ValueError("Invalid date format. Use YYYY-MM-DD or DD/MM/YYYY")

# -----------------------------
# 1) Create Shift
# -----------------------------
@shift_bp.route("", methods=["POST"])
@token_required
@role_required(MANAGE_ROLES)
def create_shift():
    data = request.get_json() or {}

    required = ["shift_name", "start_time", "end_time"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"message": f"Missing fields: {missing}"}), 400

    shift_name = data["shift_name"].strip()

    # Unique per company
    if Shift.query.filter_by(company_id=g.user.company_id, shift_name=shift_name).first():
        return jsonify({"message": "Shift name already exists"}), 409

    try:
        start_t = _parse_time(data["start_time"])
        end_t = _parse_time(data["end_time"])
    except Exception as e:
        return jsonify({"message": str(e)}), 400

    new_shift = Shift(
        company_id=g.user.company_id,
        shift_name=shift_name,
        start_time=start_t,
        end_time=end_t,
        weekly_off=data.get("weekly_off", "Sunday"),
        description=data.get("description"),
        is_active=data.get("is_active", "Yes")
    )
    db.session.add(new_shift)
    db.session.commit()

    return jsonify({"message": "Shift created", "shift_id": new_shift.shift_id}), 201

# -----------------------------
# 2) List Shifts
# -----------------------------
@shift_bp.route("", methods=["GET"])
@token_required
@role_required(MANAGE_ROLES)
def list_shifts():
    shifts = Shift.query.filter_by(company_id=g.user.company_id).order_by(Shift.shift_id.desc()).all()

    output = []
    for s in shifts:
        output.append({
            "shift_id": s.shift_id,
            "shift_name": s.shift_name,
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "weekly_off": s.weekly_off,
            "description": s.description,
            "is_active": s.is_active
        })

    return jsonify({"shifts": output, "count": len(output)}), 200

# -----------------------------
# 3) Update Shift
# -----------------------------
@shift_bp.route("/<int:shift_id>", methods=["PUT"])
@token_required
@role_required(MANAGE_ROLES)
def update_shift(shift_id):
    data = request.get_json() or {}
    s = Shift.query.get(shift_id)

    if not s or s.company_id != g.user.company_id:
        return jsonify({"message": "Shift not found"}), 404

    if "shift_name" in data and data["shift_name"]:
        new_name = data["shift_name"].strip()
        exists = Shift.query.filter_by(company_id=g.user.company_id, shift_name=new_name).first()
        if exists and exists.shift_id != shift_id:
            return jsonify({"message": "Shift name already exists"}), 409
        s.shift_name = new_name

    try:
        if "start_time" in data and data["start_time"]:
            s.start_time = _parse_time(data["start_time"])
        if "end_time" in data and data["end_time"]:
            s.end_time = _parse_time(data["end_time"])
    except Exception as e:
        return jsonify({"message": str(e)}), 400

    if "weekly_off" in data:
        s.weekly_off = data.get("weekly_off") or s.weekly_off
    if "description" in data:
        s.description = data.get("description")
    if "is_active" in data:
        s.is_active = data.get("is_active") or s.is_active

    db.session.commit()
    return jsonify({"message": "Shift updated"}), 200

# -----------------------------
# 4) Delete Shift
# -----------------------------
@shift_bp.route("/<int:shift_id>", methods=["DELETE"])
@token_required
@role_required(MANAGE_ROLES)
def delete_shift(shift_id):
    s = Shift.query.get(shift_id)
    if not s or s.company_id != g.user.company_id:
        return jsonify({"message": "Shift not found"}), 404

    # If assignments exist, block delete
    any_assign = ShiftAssignment.query.filter_by(company_id=g.user.company_id, shift_id=shift_id).first()
    if any_assign:
        return jsonify({"message": "Shift has assignments. Remove assignments first."}), 409

    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "Shift deleted"}), 200

# -----------------------------
# 5) Assign shift to employee
# -----------------------------
@shift_bp.route("/assign", methods=["POST"])
@token_required
@role_required(MANAGE_ROLES)
def assign_shift():
    data = request.get_json() or {}
    required = ["employee_id", "shift_id", "start_date"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"message": f"Missing fields: {missing}"}), 400

    emp = Employee.query.get(int(data["employee_id"]))
    if not emp or emp.company_id != g.user.company_id:
        return jsonify({"message": "Employee not found"}), 404

    s = Shift.query.get(int(data["shift_id"]))
    if not s or s.company_id != g.user.company_id:
        return jsonify({"message": "Shift not found"}), 404

    try:
        start_d = _parse_date(data["start_date"])
        end_d = _parse_date(data["end_date"]) if data.get("end_date") else None
    except Exception as e:
        return jsonify({"message": str(e)}), 400

    # prevent duplicates for same employee start_date
    exists = ShiftAssignment.query.filter_by(
        company_id=g.user.company_id,
        employee_id=emp.id,
        start_date=start_d
    ).first()
    if exists:
        return jsonify({"message": "Shift assignment already exists for this employee and start_date"}), 409

    a = ShiftAssignment(
        company_id=g.user.company_id,
        employee_id=emp.id,
        shift_id=s.shift_id,
        start_date=start_d,
        end_date=end_d
    )
    db.session.add(a)
    db.session.commit()

    return jsonify({"message": "Shift assigned", "assignment_id": a.assignment_id}), 201

# -----------------------------
# 6) List assignments
# -----------------------------
@shift_bp.route("/assignments", methods=["GET"])
@token_required
@role_required(MANAGE_ROLES)
def list_assignments():
    rows = ShiftAssignment.query.filter_by(company_id=g.user.company_id).order_by(ShiftAssignment.assignment_id.desc()).all()
    output = []
    for a in rows:
        output.append({
            "assignment_id": a.assignment_id,
            "employee_id": a.employee_id,
            "shift_id": a.shift_id,
            "start_date": a.start_date.isoformat(),
            "end_date": a.end_date.isoformat() if a.end_date else None
        })
    return jsonify({"assignments": output, "count": len(output)}), 200

# -----------------------------
# 7) Delete assignment
# -----------------------------
@shift_bp.route("/assign/<int:assignment_id>", methods=["DELETE"])
@token_required
@role_required(MANAGE_ROLES)
def delete_assignment(assignment_id):
    a = ShiftAssignment.query.get(assignment_id)
    if not a or a.company_id != g.user.company_id:
        return jsonify({"message": "Assignment not found"}), 404

    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Assignment deleted"}), 200