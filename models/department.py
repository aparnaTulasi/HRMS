from datetime import datetime
from models import db

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    department_code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to the Employee who is the manager
    manager = db.relationship('Employee', foreign_keys=[manager_id])

    def __repr__(self):
        return f"<Department {self.department_name}>"