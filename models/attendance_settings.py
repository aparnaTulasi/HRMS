from datetime import datetime
from models import db

class AttendanceSettings(db.Model):
    __tablename__ = 'attendance_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, unique=True)
    
    # Sync Settings
    auto_sync = db.Column(db.Boolean, default=True)
    sync_interval_minutes = db.Column(db.Integer, default=30)
    
    # Other settings can go here
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company', backref='attendance_settings', uselist=False)
