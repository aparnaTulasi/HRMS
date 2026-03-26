from models import db
from datetime import datetime, date

class JobPosting(db.Model):
    __tablename__ = 'job_postings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    employment_type = db.Column(db.String(50), default='Full-time') # Full-time, Contract, etc.
    location = db.Column(db.String(50), default='Remote') # Office, Remote, Hybrid
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    status = db.Column(db.String(20), default='Open') # Open, Closed
    posted_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to applicants
    applicants = db.relationship('JobApplicant', backref='job', lazy=True, cascade="all, delete-orphan")
    department = db.relationship('Department', backref='job_postings', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "job_title": self.job_title,
            "department": self.department.department_name if self.department else "General",
            "department_id": self.department_id,
            "employment_type": self.employment_type,
            "location": self.location,
            "description": self.description,
            "requirements": self.requirements,
            "status": self.status,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "applicant_count": len(self.applicants)
        }
