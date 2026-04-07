# models/delegation.py
from datetime import datetime
from models import db

class Delegation(db.Model):
    __tablename__ = 'delegations'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    
    # The person who is giving away their authority
    delegated_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    
    # The person who is receiving the authority
    delegated_to_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    
    # Scope of delegation (e.g., 'Leave', 'Expense', 'All')
    module = db.Column(db.String(50), nullable=False, default='All')
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    notes = db.Column(db.Text)
    
    # Status: ACTIVE, CANCELLED, EXPIRED
    status = db.Column(db.String(20), default='ACTIVE', nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    delegator = db.relationship('Employee', foreign_keys=[delegated_by_id], backref='given_delegations')
    delegatee = db.relationship('Employee', foreign_keys=[delegated_to_id], backref='received_delegations')
