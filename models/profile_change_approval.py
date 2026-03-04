from datetime import datetime
from models import db

class ProfileChangeApproval(db.Model):
    __tablename__ = 'profile_change_approvals'
    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(db.Integer, db.ForeignKey('profile_change_requests.id'), nullable=False)
    approver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    action = db.Column(db.String(20), nullable=False)  # APPROVE / REJECT / FORWARD
    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)