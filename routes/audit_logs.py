from flask import Blueprint, request, jsonify, g
from utils.decorators import token_required
from models.audit_log import AuditLog
from models.user import User
from models.employee import Employee
from models import db

audit_bp = Blueprint("audit", __name__)

@audit_bp.route("/api/audit/logs", methods=["GET"])
@token_required
def get_audit_logs():
    """
    Retrieves audit logs based on a strict 5-tier access hierarchy:
    1. Super Admin: All logs.
    2. Admin: Company-wide (excludes other companies).
    3. HR: Company Managers & Employees only.
    4. Manager: Self and direct subordinates only.
    5. Employee: Self logs only.
    """
    user = g.user
    role = user.role.upper()
    
    print(f"[DEBUG] Audit Logs Request - User: {user.email}, Role: {role}, CoID: {user.company_id}")
    
    # Base query
    query = AuditLog.query

    # --- 1. ACCESS HIERARCHY FILTERS ---
    if role == "SUPER_ADMIN":
        pass  # sees everything
    elif role == "ADMIN":
        query = query.filter(AuditLog.company_id == user.company_id)
        # Note: If restricted strictly to "HR, Manager, Employee", then:
        # query = query.filter(AuditLog.role.in_(['HR', 'MANAGER', 'EMPLOYEE']))
    elif role == "HR":
        query = query.filter(
            AuditLog.company_id == user.company_id,
            AuditLog.role.in_(['MANAGER', 'EMPLOYEE'])
        )
    elif role == "MANAGER":
        manager_emp = Employee.query.filter_by(user_id=user.id).first()
        if manager_emp:
            subordinate_user_ids = [e.user_id for e in Employee.query.filter_by(manager_id=manager_emp.id).all() if e.user_id]
            allowed_user_ids = [user.id] + subordinate_user_ids
            query = query.filter(AuditLog.user_id.in_(allowed_user_ids))
        else:
            query = query.filter(AuditLog.user_id == user.id)
    else: # Default to Employee level
        query = query.filter(AuditLog.user_id == user.id)

    # --- 2. QUERY PARAM FILTERS ---
    if request.args.get("user_id"):
        query = query.filter(AuditLog.user_id == request.args["user_id"])
    if request.args.get("action"):
        query = query.filter(AuditLog.action.ilike(f'%{request.args["action"]}%'))
    if request.args.get("module"):
        query = query.filter(AuditLog.module.ilike(f'%{request.args["module"]}%'))
    if request.args.get("status"):
        query = query.filter(AuditLog.status == request.args["status"].upper())
    
    # Time Optimizations
    if request.args.get("year"):
        query = query.filter(AuditLog.year == int(request.args["year"]))
    if request.args.get("month"):
        query = query.filter(AuditLog.month == int(request.args["month"]))
    if request.args.get("day"):
        query = query.filter(AuditLog.day == int(request.args["day"]))

    # Pagination
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    
    # Sort and Pagination
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    logs = pagination.items
    
    print(f"[DEBUG] Audit Logs Count: {len(logs)} / {pagination.total}")

    return jsonify({
        "success": True,
        "total": pagination.total,
        "page": page,
        "limit": limit,
        "data": [{
            "id": log.id,
            "action": log.action,
            "entity": log.entity,
            "entity_id": log.reference_id or f"EID-{log.entity_id}",
            "performed_by": log.user_name or "System",
            "role": log.role,
            "date_time": log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else "N/A",
            "ip_address": log.ip_address,
            "details": log.description,
            "module": log.module,
            "status": log.status,
            "old_data": log.old_data,
            "new_data": log.new_data
        } for log in logs]
    })

@audit_bp.route("/api/audit/my-logs", methods=["GET"])
@token_required
def my_logs():
    """
    Simplified personal logs for the current user.
    """
    logs = AuditLog.query \
        .filter(AuditLog.user_id == g.user.id) \
        .order_by(AuditLog.created_at.desc()) \
        .all()

    return jsonify({
        "success": True,
        "data": [{
            "action": l.action,
            "module": l.module,
            "details": l.description,
            "status": l.status,
            "created_at": l.created_at.strftime('%Y-%m-%d %H:%M') if l.created_at else None
        } for l in logs]
    })