from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from models import db
from models.attendance import Attendance
from models.hr_documents import WFHRequest
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, role_required
from sqlalchemy import func

wfh_bp = Blueprint("wfh", __name__)

ALLOWED_MANAGE_ROLES = ["SUPER_ADMIN", "ADMIN", "HR", "MANAGER"]

def _parse_date(value: str) -> date:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None

@wfh_bp.route("/summary", methods=["GET"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def wfh_summary():
    company_id = g.user.company_id
    if g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get("company_id") or company_id

    query = WFHRequest.query
    if company_id:
        query = query.filter_by(company_id=company_id)

    total = query.count()
    pending = query.filter_by(status="PENDING").count()
    approved = query.filter_by(status="APPROVED").count()
    rejected = query.filter_by(status="REJECTED").count()

    return jsonify({
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }), 200

@wfh_bp.route("/requests", methods=["GET"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def list_wfh_requests():
    company_id = g.user.company_id
    if g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get("company_id") or company_id

    status = request.args.get("status")
    search = (request.args.get("search") or "").strip().lower()

    query = db.session.query(WFHRequest).join(Employee, WFHRequest.employee_id == Employee.id)
    
    if company_id:
        query = query.filter(WFHRequest.company_id == company_id)
    
    if status and status != "All":
        query = query.filter(WFHRequest.status == status.upper())

    if search:
        query = query.filter(
            db.or_(
                func.lower(Employee.first_name).like(f"%{search}%"),
                func.lower(Employee.last_name).like(f"%{search}%"),
                func.lower(Employee.department).like(f"%{search}%")
            )
        )

    requests = query.order_by(WFHRequest.created_at.desc()).all()

    output = []
    for r in requests:
        emp = r.employee_rel
        output.append({
            "id": r.id,
            "employee_name": emp.full_name if emp else "Unknown",
            "department": emp.department if emp else "N/A",
            "period": f"{r.from_date} - {r.to_date}",
            "from_date": r.from_date.isoformat(),
            "to_date": r.to_date.isoformat(),
            "days": (r.to_date - r.from_date).days + 1,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        })

    return jsonify(output), 200

@wfh_bp.route("/allocate", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def allocate_wfh():
    data = request.get_json()
    employee_id = data.get("employee_id") # Can be string code or int ID
    from_date = _parse_date(data.get("from_date"))
    to_date = _parse_date(data.get("to_date"))
    reason = data.get("reason")

    if not all([employee_id, from_date, to_date]):
        return jsonify({"message": "employee_id, from_date, and to_date are required"}), 400

    # Find employee
    emp = Employee.query.filter_by(employee_id=str(employee_id)).first()
    if not emp and str(employee_id).isdigit():
        emp = Employee.query.get(int(employee_id))
    
    if not emp:
        return jsonify({"message": "Employee not found"}), 404
    
    if g.user.role != 'SUPER_ADMIN' and emp.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403

    new_request = WFHRequest(
        company_id=emp.company_id,
        employee_id=emp.id,
        from_date=from_date,
        to_date=to_date,
        reason=reason,
        status="PENDING"
    )

    db.session.add(new_request)
    db.session.commit()

    return jsonify({"message": "WFH allocated successfully", "id": new_request.id}), 201

@wfh_bp.route("/<int:id>/approve", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def approve_wfh(id):
    req = WFHRequest.query.get_or_404(id)
    if g.user.role != 'SUPER_ADMIN' and req.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403
    
    req.status = "APPROVED"
    req.approved_by = g.user.id
    
    # Optional: Update attendance logs to "WFH" for the period
    # ... logic to mark attendance as WFH for each day between from_date and to_date
    
    db.session.commit()
    return jsonify({"message": "WFH request approved"}), 200

@wfh_bp.route("/<int:id>/reject", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def reject_wfh(id):
    req = WFHRequest.query.get_or_404(id)
    if g.user.role != 'SUPER_ADMIN' and req.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403
    
    req.status = "REJECTED"
    req.approved_by = g.user.id
    db.session.commit()
    return jsonify({"message": "WFH request rejected"}), 200
