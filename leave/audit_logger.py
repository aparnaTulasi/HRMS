from flask import request, g
from models import db
from models.audit_log import AuditLog

def log_action(action, entity, entity_id=None, status_code=200, meta=None):
    try:
        # Use g.user if available (set by token_required), otherwise fallback to None/SYSTEM
        user = g.get('user')
        
        log = AuditLog(
            company_id = getattr(user, "company_id", None) if user else None,
            user_id = getattr(user, "id", None) if user else None,
            role = getattr(user, "role", "SYSTEM") if user else "SYSTEM",

            action = action,
            entity = entity,
            entity_id = entity_id,

            method = request.method,
            path = request.path,
            status_code = status_code,

            ip_address = request.remote_addr,
            user_agent = request.headers.get("User-Agent"),
            meta = meta
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()