from datetime import datetime
from models import db

class Attendance(db.Model):
    __tablename__ = 'attendance_logs'
    attendance_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    # We keep 'date' for easier querying, though strictly not in the prompt's SQL, it's implied by punch times or needed for unique constraints
    date = db.Column(db.Date, default=datetime.utcnow().date) 
    punch_in_time = db.Column(db.DateTime)
    punch_out_time = db.Column(db.DateTime)
    total_hours = db.Column(db.Float, default=0.0)
    location = db.Column(db.String(200))
    capture_method = db.Column(db.String(50), default='Web', nullable=False) # Web, Biometric, Mobile
    status = db.Column(db.String(20), default='Present', nullable=False) # Present, Absent, Leave
    regularization_status = db.Column(db.String(20), default='N/A', nullable=False) # N/A, Pending, Approved, Rejected
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
