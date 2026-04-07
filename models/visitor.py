# models/visitor.py
from datetime import datetime, date
from models import db

class VisitorRequest(db.Model):
    __tablename__ = 'visitor_requests'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    
    # Visitor Details
    visitor_name = db.Column(db.String(150), nullable=False)
    organization = db.Column(db.String(150))
    phone_number = db.Column(db.String(20))
    
    # Visit Details
    visit_date = db.Column(db.Date, nullable=False, index=True)
    preferred_time = db.Column(db.String(20)) # e.g. "02:00 PM"
    purpose = db.Column(db.Text)
    
    # Internal Meeting Details
    meeting_with_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    
    # Status: PENDING, APPROVED, REJECTED, CHECKED_IN, CHECKED_OUT
    status = db.Column(db.String(20), default='PENDING', nullable=False, index=True)
    
    # Audit & Flow
    check_in_time = db.Column(db.DateTime, nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=True)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Who approved/rejected
    action_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', backref='visitor_requests', foreign_keys=[meeting_with_employee_id])
