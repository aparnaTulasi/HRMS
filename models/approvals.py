from datetime import datetime
from models import db

class ApprovalRequest(db.Model):
    __tablename__ = 'approval_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(50), nullable=False)  # LEAVE, EXPENSE, POLICY_EXCEPTION
    resource_id = db.Column(db.Integer, nullable=False)      # ID of the linked resource (e.g., Leave ID)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='PENDING')     # PENDING, APPROVED, REJECTED
    current_step_order = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = db.relationship('ApprovalStep', backref='request', lazy=True, order_by='ApprovalStep.step_order', cascade="all, delete-orphan")
    actions = db.relationship('ApprovalAction', backref='request', lazy=True, order_by='ApprovalAction.performed_at')

class ApprovalStep(db.Model):
    __tablename__ = 'approval_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('approval_requests.id'), nullable=False)
    step_name = db.Column(db.String(100), nullable=False)    # e.g., "Manager Approval"
    step_order = db.Column(db.Integer, nullable=False)       # 1, 2, 3...
    role_required = db.Column(db.String(50), nullable=True)  # e.g., MANAGER, HR
    specific_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='PENDING')     # PENDING, APPROVED, REJECTED, SKIPPED

class ApprovalAction(db.Model):
    __tablename__ = 'approval_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('approval_requests.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('approval_steps.id'), nullable=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)        # APPROVE, REJECT, COMMENT
    comments = db.Column(db.Text)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)