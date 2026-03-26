from models import db
from datetime import datetime

class Squad(db.Model):
    __tablename__ = 'squads'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    squad_name = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(100))
    squad_type = db.Column(db.String(50), default='IT') # IT, Non-IT
    status = db.Column(db.String(20), default='Active')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('SquadMember', backref='squad', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "squad_name": self.squad_name,
            "project_name": self.project_name,
            "squad_type": self.squad_type,
            "status": self.status,
            "member_count": len(self.members)
        }
