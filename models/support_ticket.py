from datetime import datetime
from models import db

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.String(50), nullable=False, unique=True)
    subject = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    priority = db.Column(db.String(50), nullable=False, default='Medium')
    status = db.Column(db.String(50), nullable=False, default='Open')
    description = db.Column(db.Text, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # or super_admins
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.ticket_id,
            'db_id': self.id,
            'subject': self.subject,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'description': self.description,
            'company_id': self.company_id,
            'created_by': self.created_by,
            'date': self.created_at.strftime('%Y-%m-%d'),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
