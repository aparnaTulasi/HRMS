from datetime import datetime
from models import db

class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rating = db.Column(db.String(50), nullable=False) # e.g., 'Loved It!', 'It's Okay', 'Needs Help'
    category = db.Column(db.String(100), nullable=False) # e.g., 'User Interface', 'Performance', etc.
    comments = db.Column(db.Text, nullable=True)
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'rating': self.rating,
            'category': self.category,
            'comments': self.comments,
            'company_id': self.company_id,
            'date': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
