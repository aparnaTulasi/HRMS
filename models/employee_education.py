from datetime import datetime
from models import db

class EmployeeEducation(db.Model):
    __tablename__ = 'employee_education'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    institution = db.Column(db.String(255), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    field_of_study = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    percentage = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "institution": self.institution,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "percentage": self.percentage
        }
