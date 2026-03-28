from flask import Blueprint, request, jsonify, g
from utils.decorators import token_required
from models.audit_log import AuditLog
from models.user import User
from models import db

audit_bp = Blueprint("audit", __name__)

# 🔹 Helplers for UI Formatting
def _get_module(entity):
    mapping = {
        'User': 'Auth',
        'AUTH': 'Auth',
        'Employee': 'Employee',
        'Attendance': 'Employee',
        'LeaveRequest': 'Employee',
        'Leave': 'Employee',
        'Shift': 'Employee',
        'Payroll': 'Finance',
        'Loan': 'Finance',
        'Payslip': 'Finance',
        'Company': 'Company',
        'Branch': 'Company',
        'Department': 'Company',
        'Designation': 'Company'
    }
    return mapping.get(entity, 'System')

def _format_entity_id(entity, eid):
    if not eid: return "N/A"
    prefixes = {
        'Employee': 'EMP',
        'Company': 'COMP',
        'Document': 'DOC',
        'Payroll': 'PAY',
        'User': 'USR'
    }
    prefix = prefixes.get(entity, 'SYS')
    return f"{prefix}-{eid}"

def _generate_details(log, user):
    act = log.action.upper()
    ent = log.entity
    role = log.role or "System"
    
    if "LOGIN" in act:
        return f"Successful login to {role} Dashboard"
    
    # Try to extract name from meta if available
    name = "Record"
    import json
    try:
        if log.meta:
            meta_dict = json.loads(log.meta.replace("'", '"')) if isinstance(log.meta, str) else log.meta
            name = meta_dict.get('name') or meta_dict.get('full_name') or meta_dict.get('company_name') or name
    except:
        pass

    if "CREATE" in act:
        return f"Created new {ent}: {name}"
    if "UPDATE" in act:
        return f"Updated {ent} details for {name}"
    if "DELETE" in act:
        return f"Deleted {ent}: {name}"
    
    return f"Performed {act} on {ent}"

# 🔹 Admin / HR / Super Admin
@audit_bp.route("/api/audit/logs", methods=["GET"])
@token_required
def get_audit_logs():
    # Role check
    if g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
        return jsonify({"message": "Unauthorized"}), 403

    query = db.session.query(AuditLog, User).outerjoin(User, AuditLog.user_id == User.id)

    # company isolation
    if g.user.role != "SUPER_ADMIN":
        query = query.filter(AuditLog.company_id == g.user.company_id)

    # filters
    if request.args.get("user_id"):
        query = query.filter(AuditLog.user_id == request.args["user_id"])
    if request.args.get("action"):
        query = query.filter(AuditLog.action.ilike(f'%{request.args["action"]}%'))
    if request.args.get("entity"):
        query = query.filter(AuditLog.entity.ilike(f'%{request.args["entity"]}%'))
    
    # Module filter
    module_filter = request.args.get("module")
    
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    all_logs = query.order_by(AuditLog.created_at.desc()).all()
    
    data = []
    for log, user in all_logs:
        log_module = _get_module(log.entity)
        if module_filter and module_filter.lower() != log_module.lower():
            continue
            
        performer_name = "System"
        if user:
            performer_name = user.name
        elif log.user_id:
            performer_name = f"User {log.user_id}"

        data.append({
            "id": log.id,
            "action": log.action,
            "entity": log.entity,
            "entity_id": _format_entity_id(log.entity, log.entity_id),
            "performer_name": performer_name,
            "role": log.role or (user.role if user else "SYSTEM"),
            "date_time": log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else "N/A",
            "ip_address": log.ip_address or "N/A",
            "details": _generate_details(log, user),
            "module": log_module
        })

    # Manual pagination after module filtering
    total = len(data)
    start = (page - 1) * limit
    end = start + limit
    paginated_data = data[start:end]

    return jsonify({
        "success": True,
        "page": page,
        "limit": limit,
        "total": total,
        "data": paginated_data
    })


# 🔹 Employee – My Logs
@audit_bp.route("/api/audit/my-logs", methods=["GET"])
@token_required
def my_logs():
    logs = AuditLog.query \
        .filter(AuditLog.user_id == g.user.id) \
        .order_by(AuditLog.created_at.desc()) \
        .all()

    return jsonify({
        "success": True,
        "data": [{
            "action": l.action,
            "entity": l.entity,
            "entity_id": l.entity_id,
            "method": l.method,
            "path": l.path,
            "status_code": l.status_code,
            "created_at": l.created_at
        } for l in logs]
    })