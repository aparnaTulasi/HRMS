from datetime import datetime
from models import db
from sqlalchemy import CheckConstraint

class LeaveType(db.Model):
    __tablename__ = 'leave_types'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    name = db.Column(db.String(50), nullable=False)
    is_paid = db.Column(db.String(10), default='Yes', nullable=False) # Yes/No
    max_days_per_year = db.Column(db.Integer, default=12)
    
    __table_args__ = (
        db.UniqueConstraint('name', 'company_id', name='uq_leave_type_name_company'),
        CheckConstraint("is_paid IN ('Yes', 'No')", name='chk_is_paid'),
        CheckConstraint('max_days_per_year >= 0', name='chk_max_days'),
    )
    
    leaves = db.relationship('LeaveRequest', backref='leave_type', lazy=True)
    balances = db.relationship('LeaveBalance', backref='leave_type', lazy=True)

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Float)
    reason = db.Column(db.String(300))
    status = db.Column(db.String(20), default='Pending', nullable=False) # Pending/Approved/Rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    document_attachment = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected')", name='chk_status'),
        CheckConstraint('total_days >= 0', name='chk_req_total_days'),
        CheckConstraint('end_date >= start_date', name='chk_dates'),
    )
    
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    approver = db.relationship('Employee', foreign_keys=[approved_by])

class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    
    total_days = db.Column(db.Float, default=12.0, nullable=False)
    used_days = db.Column(db.Float, default=0.0, nullable=False)
    remaining_days = db.Column(db.Float, default=12.0, nullable=False)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'leave_type_id', name='pk_leave_balance_unique'),
        CheckConstraint('total_days >= 0', name='chk_total_days'),
        CheckConstraint('used_days >= 0', name='chk_used_days'),
        CheckConstraint('remaining_days >= 0', name='chk_remaining_days'),
    )
    
    employee = db.relationship('Employee', backref='leave_balances')
    # leave_type relationship is defined in LeaveType via backref