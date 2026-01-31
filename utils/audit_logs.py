from flask import Blueprint, request, jsonify, g
from utils.decorators import token_required
from models.audit_log import AuditLog
from models import db

audit_bp = Blueprint("audit", __name__)

# 🔹 Admin / HR / Super Admin
@audit_bp.route("/api/audit/logs", methods=["GET"])
@token_required
def get_audit_logs():
    # Role check
    if g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
        return jsonify({"message": "Unauthorized"}), 403

    query = AuditLog.query

    # company isolation
    if g.user.role != "SUPER_ADMIN":
        query = query.filter(AuditLog.company_id == g.user.company_id)

    # filters
    if request.args.get("user_id"):
        query = query.filter(AuditLog.user_id == request.args["user_id"])
    if request.args.get("action"):
        query = query.filter(AuditLog.action == request.args["action"])
    if request.args.get("entity"):
        query = query.filter(AuditLog.entity == request.args["entity"])

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    pagination = query.order_by(AuditLog.created_at.desc()) \
                      .paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        "success": True,
        "page": page,
        "limit": limit,
        "total": pagination.total,
        "data": [{
            "id": l.id,
            "user_id": l.user_id,
            "role": l.role,
            "action": l.action,
            "entity": l.entity,
            "entity_id": l.entity_id,
            "method": l.method,
            "path": l.path,
            "status_code": l.status_code,
            "ip_address": l.ip_address,
            "created_at": l.created_at
        } for l in pagination.items]
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