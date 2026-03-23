from datetime import datetime
from models import db

class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=True) # e.g., '09:00'
    end_time = db.Column(db.String(10), nullable=True) # e.g., '10:00'
    type = db.Column(db.String(50), nullable=False, default='work') # work, personal, important
    description = db.Column(db.Text, nullable=True)
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'time': f"{self.start_time or ''} - {self.end_time or ''}".strip(' -'),
            'type': self.type,
            'description': self.description,
            'company_id': self.company_id,
            'created_by': self.created_by
        }
