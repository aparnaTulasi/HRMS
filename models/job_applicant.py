from models import db
from datetime import datetime

class JobApplicant(db.Model):
    __tablename__ = 'job_applicants'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    current_stage = db.Column(db.String(50), default='Applied') # Applied, Interview, Hired, Rejected
    applied_date = db.Column(db.Date, default=datetime.utcnow().date)
    resume_url = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "full_name": self.full_name,
            "email": self.email,
            "current_stage": self.current_stage,
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "resume_url": self.resume_url
        }
