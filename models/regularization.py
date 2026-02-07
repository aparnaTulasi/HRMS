from datetime import datetime
from models import db

class AttendanceRegularization(db.Model):
    __tablename__ = 'attendance_regularizations'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    requested_login_at = db.Column(db.DateTime, nullable=True)
    requested_logout_at = db.Column(db.DateTime, nullable=True)
    requested_status = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='PENDING') # PENDING / APPROVED / REJECTED
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = db.relationship('Company', backref='regularization_requests')
    user = db.relationship('User', foreign_keys=[user_id], backref='regularization_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])