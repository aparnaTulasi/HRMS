from datetime import datetime
from models import db

class ProfileChangeRequest(db.Model):
    __tablename__ = 'profile_change_requests'
    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(db.Integer, nullable=False)

    requester_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    status = db.Column(db.String(20), default='PENDING')  
    # PENDING -> APPROVED -> REJECTED -> ESCALATED -> APPLIED

    # ✅ Workflow Fields
    requested_by_role = db.Column(db.String(50))
    current_approver_role = db.Column(db.String(50))
    
    flow_type = db.Column(db.String(50), nullable=False) # EMP_TO_HR, HR_TO_SA, SA_TO_ROOT
    approver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Specific approver

    reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship('ProfileChangeRequestItem', backref='request', lazy=True, cascade="all, delete-orphan")