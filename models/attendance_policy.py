from datetime import datetime
from models import db

class AttendancePolicy(db.Model):
    __tablename__ = 'attendance_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, unique=True)
    
    # Grace time for late-in (in minutes)
    grace_time_minutes = db.Column(db.Integer, default=15)
    
    # Work hours for half-day / full-day
    half_day_hours = db.Column(db.Float, default=4.0)
    full_day_hours = db.Column(db.Float, default=8.0)
    
    # Rules for late marks
    late_marks_limit = db.Column(db.Integer, default=3) # e.g. 3 late marks = 1 half day deduction (logic outside)
    
    # Shift Settings
    shift_buffer_minutes = db.Column(db.Integer, default=30)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company', backref='attendance_policy', uselist=False)
