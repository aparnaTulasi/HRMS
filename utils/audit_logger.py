from flask import request, g
from models import db
from models.audit_log import AuditLog

def log_action(action, entity, entity_id=None, status_code=200, meta=None):
    """
    Creates an audit log row.
    Safe logging: never store passwords/otp in meta.
    """
    try:
        # Use g.user set by the token_required decorator, not current_user
        user = g.get('user')
        
        # Safe access to request properties
        method = None
        path = None
        remote_addr = None
        user_agent = None
        
        try:
            method = request.method
            path = request.path
            remote_addr = request.remote_addr
            user_agent = request.headers.get("User-Agent")
        except RuntimeError:
            # Outside request context
            pass

        log = AuditLog(
            company_id=getattr(user, "company_id", None),
            user_id=getattr(user, "id", None),
            role=getattr(user, "role", "SYSTEM") if user else "SYSTEM",

            action=action,
            entity=entity,
            entity_id=entity_id,

            method=method or "N/A",
            path=path or "N/A",
            status_code=status_code,

            ip_address=remote_addr or "0.0.0.0",
            user_agent=user_agent or "N/A",
            meta=str(meta) if meta else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
