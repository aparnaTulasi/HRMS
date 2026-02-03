from datetime import datetime
from models import db

class Shift(db.Model):
    __tablename__ = "shifts"

    shift_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    shift_name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    weekly_off = db.Column(db.String(20), default="Sunday")
    description = db.Column(db.String(255))
    is_active = db.Column(db.String(10), default="Yes")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ShiftAssignment(db.Model):
    __tablename__ = "shift_assignments"

    assignment_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.shift_id"), nullable=False)
    
    shift_name = db.Column(db.String(100))
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)