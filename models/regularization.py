from datetime import datetime
from models import db

class RegularizationRequest(db.Model):
    __tablename__ = 'regularization_requests'
    request_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance_logs.attendance_id'), nullable=True)
    request_date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    reason = db.Column(db.String(300))
    requested_punch_in = db.Column(db.DateTime)
    requested_punch_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Pending') # Pending/Approved/Rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref='regularization_requests')
    attendance = db.relationship('Attendance', backref='regularization_requests')
    approver = db.relationship('Employee', foreign_keys=[approved_by])

    # Check constraint logic is handled at application level or DB migration level