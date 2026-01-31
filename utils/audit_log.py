from models import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=True)

    user_id = db.Column(db.Integer, nullable=True)
    role = db.Column(db.String(50))

    action = db.Column(db.String(100), nullable=False)
    entity = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)

    method = db.Column(db.String(10))
    path = db.Column(db.String(255))
    status_code = db.Column(db.Integer)

    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))

    meta = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)