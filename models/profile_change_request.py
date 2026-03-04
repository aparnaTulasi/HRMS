from datetime import datetime
from models import db

class ProfileChangeRequest(db.Model):
    __tablename__ = 'profile_change_requests'
    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(db.Integer, nullable=False)

    requester_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    status = db.Column(db.String(20), default='PENDING')  
    # PENDING -> APPROVED -> REJECTED -> APPLIED

    # ✅ New Flow Fields
    flow_type = db.Column(db.String(50), nullable=False) # EMP_TO_HR, HR_TO_SA, SA_TO_ROOT
    approver_role = db.Column(db.String(50), nullable=False) # MANAGER/HR_MANAGER, SUPER_ADMIN, ROOT_ADMIN
    approver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Specific approver

    reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship('ProfileChangeRequestItem', backref='request', lazy=True, cascade="all, delete-orphan")