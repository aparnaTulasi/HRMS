from models import db
from datetime import datetime

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True) # Null for Global (Super Admin)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='NORMAL') # HIGH, NORMAL, LOW
    category = db.Column(db.String(50), default='General') # Holiday, Policy, News
    is_active = db.Column(db.Boolean, default=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "category": self.category,
            "created_at": self.created_at.strftime("%d %b %Y"),
            "expiry_date": self.expiry_date.strftime("%Y-%m-%d") if self.expiry_date else None,
            "creator_name": self.creator.username if self.creator else "System"
        }
