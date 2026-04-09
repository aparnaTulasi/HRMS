from app import app, db
from models.audit_log import AuditLog
from sqlalchemy import func

with app.app_context():
    print("--- AUDIT LOG USER IDS ---")
    res = db.session.query(AuditLog.user_id, func.count(AuditLog.id)).group_by(AuditLog.user_id).all()
    for uid, count in res:
        print(f"User ID: {uid}, Count: {count}")
