from datetime import datetime
from models import db

class ApprovalRequest(db.Model):
    __tablename__ = "approval_requests"

    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(50), nullable=False)
    reference_id = db.Column(db.Integer, nullable=False)
    requested_by = db.Column(db.Integer, nullable=False)
    company_id = db.Column(db.Integer, nullable=False)

    status = db.Column(db.String(20), default="PENDING")
    current_step = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApprovalStep(db.Model):
    __tablename__ = "approval_steps"

    id = db.Column(db.Integer, primary_key=True)
    approval_request_id = db.Column(db.Integer, nullable=False)
    step_order = db.Column(db.Integer, nullable=False)

    approver_role = db.Column(db.String(20), nullable=False)  # MANAGER / HR / ADMIN
    approver_id = db.Column(db.Integer, nullable=True)

    status = db.Column(db.String(20), default="PENDING")
    action_at = db.Column(db.DateTime)


class ApprovalAction(db.Model):
    __tablename__ = "approval_actions"

    id = db.Column(db.Integer, primary_key=True)
    approval_request_id = db.Column(db.Integer, nullable=False)
    action_by = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20), nullable=False)  # APPROVED / REJECTED
    remarks = db.Column(db.Text)
    action_at = db.Column(db.DateTime, default=datetime.utcnow)