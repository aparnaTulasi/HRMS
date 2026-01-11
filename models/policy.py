from app import db
from datetime import datetime

class PolicyCategory(db.Model):
    __tablename__ = 'policy_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

class Policy(db.Model):
    __tablename__ = 'policies'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('policy_categories.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    effective_date = db.Column(db.Date, nullable=False)
    document_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship('PolicyCategory', backref=db.backref('policies', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'title': self.title,
            'description': self.description,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'document_url': self.document_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

class PolicyAcknowledgment(db.Model):
    __tablename__ = 'policy_acknowledgments'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure a user only acknowledges a policy once
    __table_args__ = (db.UniqueConstraint('policy_id', 'user_id', name='_policy_user_uc'),)

class PolicyViolation(db.Model):
    __tablename__ = 'policy_violations'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # The offender
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='OPEN') # OPEN, RESOLVED, DISMISSED
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    policy = db.relationship('Policy', backref=db.backref('violations', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id], backref='policy_violations')
    reported_by = db.relationship('User', foreign_keys=[reported_by_id], backref='reported_violations')

class PolicyException(db.Model):
    __tablename__ = 'policy_exceptions'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='PENDING') # PENDING, APPROVED, REJECTED
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    policy = db.relationship('Policy', backref=db.backref('exceptions', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id], backref='policy_exceptions')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_exceptions')