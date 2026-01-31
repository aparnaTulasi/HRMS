from datetime import datetime
from models import db

class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)
    document_number = db.Column(db.String(100))
    document_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_url = db.Column(db.String(500))
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentType(db.Model):
    __tablename__ = 'document_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=False)
    requires_expiry_date = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)