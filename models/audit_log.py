from models import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.BigInteger, primary_key=True)
    
    # Performer details
    user_id = db.Column(db.Integer, index=True)
    user_name = db.Column(db.String(100))
    role = db.Column(db.String(50), index=True)
    company_id = db.Column(db.Integer, index=True)

    # Action / Module
    module = db.Column(db.String(50), index=True)  # e.g. employee, auth, payroll
    action = db.Column(db.String(50), index=True)  # CREATE, UPDATE, DELETE, LOGIN
    
    # Content
    description = db.Column(db.Text)               # Human readable summary
    status = db.Column(db.String(20), default="SUCCESS") # SUCCESS / FAILED
    
    # Metadata
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Detailed Data
    entity = db.Column(db.String(100))             # Model/Table name
    entity_id = db.Column(db.Integer)              # Legacy support
    reference_id = db.Column(db.String(50))         # EMP-1, PAY-5 etc
    old_data = db.Column(db.JSON, nullable=True)
    new_data = db.Column(db.JSON, nullable=True)
    meta = db.Column(db.JSON, nullable=True)       # Generic metadata

    # Time Partitions for performance
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    day = db.Column(db.Integer)
    hour = db.Column(db.Integer)

    # API response helpers
    method = db.Column(db.String(10))
    path = db.Column(db.String(255))
    status_code = db.Column(db.Integer)

    # Composite Index for Date Queries
    __table_args__ = (
        db.Index('idx_audit_date', 'year', 'month', 'day'),
    )