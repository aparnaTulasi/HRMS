from datetime import datetime
from models import db

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    assigned_by_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    submission_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pending') # Pending/InProgress/Done
    attachment_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)