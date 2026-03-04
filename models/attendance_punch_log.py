from datetime import datetime
from models import db

class AttendancePunchLog(db.Model):
    __tablename__ = 'attendance_punch_logs'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('attendance_devices.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    punch_time = db.Column(db.DateTime, nullable=False)
    punch_type = db.Column(db.String(10), nullable=False) # IN / OUT
    source = db.Column(db.String(20), default="DEVICE") # DEVICE / MOBILE / WEB
    offline_batch_id = db.Column(db.String(50))
    client_event_id = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), default='RECEIVED') # RECEIVED / PROCESSED / REJECTED
    reject_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('company_id', 'client_event_id', name='uq_company_client_event'),
    )