from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from utils.date_utils import parse_date
from models import db
from models.attendance import Attendance
from models.hr_documents import WFHRequest
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, role_required, permission_required
from sqlalchemy import func

wfh_bp = Blueprint("wfh", __name__)

ALLOWED_MANAGE_ROLES = ["SUPER_ADMIN", "ADMIN", "HR", "MANAGER"]

def is_management():
    return g.user.role in ALLOWED_MANAGE_ROLES

@wfh_bp.route("/summary", methods=["GET"])
@token_required
def wfh_summary():
    """
    Returns stats for the WFH dashboard cards.
    Context-aware: Employees see own stats, Management see company stats.
    Managers see team stats.
    """
    company_id = g.user.company_id
    
    query = WFHRequest.query.filter_by(company_id=company_id)
    
    if g.user.role == 'MANAGER':
        # Scope to manager's team
        query = query.join(Employee, WFHRequest.employee_id == Employee.id)\
                     .filter(Employee.manager_id == g.user.id)
    elif not is_management():
        emp = Employee.query.filter_by(user_id=g.user.id).first()
        if not emp:
            return jsonify({"success": True, "total_wfh": 0, "pending": 0, "approved": 0, "rejected": 0}), 200
        query = query.filter_by(employee_id=emp.id)

    total = query.count()
    pending = query.filter_by(status="PENDING").count()
    approved = query.filter_by(status="APPROVED").count()
    rejected = query.filter_by(status="REJECTED").count()

    return jsonify({
        "success": True,
        "data": {
            "total_wfh": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }
    }), 200

@wfh_bp.route("/requests", methods=["GET"])
@token_required
def list_wfh_requests():
    """
    Returns a list of WFH requests.
    Context-aware: Employees see own history, Management see company requests.
    Managers see team requests.
    """
    company_id = g.user.company_id
    
    status_filter = request.args.get("status")
    search = (request.args.get("search") or "").strip().lower()

    query = db.session.query(WFHRequest).join(Employee, WFHRequest.employee_id == Employee.id)
    
    if g.user.role == 'MANAGER':
        query = query.filter(Employee.manager_id == g.user.id)
    elif not is_management():
        emp = Employee.query.filter_by(user_id=g.user.id).first()
        if not emp:
            return jsonify({"success": True, "data": []}), 200
        query = query.filter(WFHRequest.employee_id == emp.id)
    else:
        query = query.filter(WFHRequest.company_id == company_id)
    
    if status_filter and status_filter != "All":
        query = query.filter(WFHRequest.status == status_filter.upper())

    if search:
        query = query.filter(
            db.or_(
                func.lower(Employee.full_name).like(f"%{search}%"),
                func.lower(Employee.department).like(f"%{search}%")
            )
        )

    requests = query.order_by(WFHRequest.created_at.desc()).all()

    output = []
    for r in requests:
        e = r.employee_rel
        output.append({
            "id": r.id,
            "employeeHeight": e.employee_id if e else "", # For UI mapping
            "employee_id": e.employee_id if e else "",
            "employee_name": e.full_name if e else "Unknown",
            "department": e.department if e else "N/A",
            "period": f"{r.from_date.strftime('%Y-%m-%d')} - {r.to_date.strftime('%Y-%m-%d')}",
            "from_date": r.from_date.isoformat(),
            "to_date": r.to_date.isoformat(),
            "days": (r.to_date - r.from_date).days + 1,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        })

    return jsonify({"success": True, "data": output}), 200

@wfh_bp.route("/request", methods=["POST"])
@token_required
def submit_wfh_request():
    """
    Employee submits their own WFH request.
    """
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    if not emp:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404
        
    try:
        from_date = parse_date(data.get("from_date"))
        to_date = parse_date(data.get("to_date"))
        reason = data.get("reason")

        if not from_date or not to_date:
            return jsonify({"success": False, "message": "From Date and To Date are required"}), 400

        new_request = WFHRequest(
            company_id=emp.company_id,
            employee_id=emp.id,
            employee_name=emp.full_name, # Map to "employee" column
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            status="PENDING",
            created_by=g.user.id
        )

        db.session.add(new_request)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "WFH request submitted successfully", 
            "data": {"id": new_request.id}
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@wfh_bp.route("/allocate", methods=["POST"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def allocate_wfh():
    """
    Managers/HR/Admin directly assign WFH to an employee.
    Status is APPROVED immediately.
    """
    data = request.get_json()
    employee_id = data.get("employee_id")
    from_date_str = data.get("from_date")
    to_date_str = data.get("to_date")
    reason = data.get("reason", "Allocated by Manager")

    if not employee_id or not from_date_str or not to_date_str:
        return jsonify({"success": False, "message": "Employee ID, From Date, and To Date are required"}), 400

    target_emp = Employee.query.get_or_404(employee_id)
    
    # Permission Check
    if g.user.role == 'MANAGER':
        if target_emp.manager_id != g.user.id:
            return jsonify({"success": False, "message": "You can only allocate WFH to your own team members"}), 403
    elif g.user.role != 'SUPER_ADMIN' and target_emp.company_id != g.user.company_id:
        return jsonify({"success": False, "message": "Employee does not belong to your company"}), 403

    try:
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        new_request = WFHRequest(
            company_id=target_emp.company_id,
            employee_id=target_emp.id,
            employee_name=target_emp.full_name,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            status="APPROVED",
            created_by=g.user.id,
            action_by=g.user.id,
            action_at=datetime.utcnow()
        )

        db.session.add(new_request)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"WFH allocated successfully to {target_emp.full_name}",
            "data": {"id": new_request.id}
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@wfh_bp.route("/export", methods=["GET"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def export_wfh_requests():
    """
    Downloads the WFH logs as CSV.
    Scoping: Manager (Team), HR/Admin (Company).
    """
    import csv
    from io import StringIO
    from flask import Response

    company_id = g.user.company_id
    query = db.session.query(WFHRequest).join(Employee, WFHRequest.employee_id == Employee.id)
    
    if g.user.role == 'MANAGER':
        query = query.filter(Employee.manager_id == g.user.id)
    else:
        query = query.filter(WFHRequest.company_id == company_id)

    requests = query.order_by(WFHRequest.created_at.desc()).all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Employee', 'Department', 'From Date', 'To Date', 'Days', 'Reason', 'Status', 'CreatedAt'])

    for r in requests:
        e = r.employee_rel
        cw.writerow([
            e.full_name if e else "N/A",
            e.department if e else "N/A",
            r.from_date.strftime('%Y-%m-%d'),
            r.to_date.strftime('%Y-%m-%d'),
            (r.to_date - r.from_date).days + 1,
            r.reason,
            r.status,
            r.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=wfh_requests.csv"}
    )

@wfh_bp.route("/<int:id>/action", methods=["PATCH"])
@token_required
@role_required(ALLOWED_MANAGE_ROLES)
def wfh_action(id):
    """
    Management Approve/Reject action.
    """
    data = request.get_json()
    req = WFHRequest.query.get_or_404(id)
    
    if g.user.role != 'SUPER_ADMIN' and req.company_id != g.user.company_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    new_status = data.get("status") # APPROVED or REJECTED
    if new_status not in ["APPROVED", "REJECTED"]:
        return jsonify({"success": False, "message": "Invalid status"}), 400
        
    req.status = new_status
    req.action_by = g.user.id
    req.action_at = datetime.utcnow()
    req.comments = data.get("comments", "")
    
    db.session.commit()
    return jsonify({"success": True, "message": f"WFH request {new_status.lower()} successfully"}), 200
