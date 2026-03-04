from datetime import datetime
from models import db

class AttendanceDevice(db.Model):
    __tablename__ = 'attendance_devices'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    device_code = db.Column(db.String(50), nullable=False)
    device_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    platform = db.Column(db.String(20)) # android / biometric / web
    is_active = db.Column(db.Boolean, default=True)
    last_seen_at = db.Column(db.DateTime)
    last_ip = db.Column(db.String(45))
    battery_percent = db.Column(db.Integer, nullable=True)
    storage_percent = db.Column(db.Integer, nullable=True)
    app_version = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company', backref='attendance_devices')
    
    __table_args__ = (db.UniqueConstraint('company_id', 'device_code', name='uq_company_device_code'),)