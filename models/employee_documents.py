from datetime import datetime
from models import db

class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)
    document_number = db.Column(db.String(100))
    document_name = db.Column(db.String(255))
    file_content = db.Column(db.LargeBinary) # Stores the actual file in DB
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # New Fields for Hierarchy and Workflow
    # Status: PENDING VERIFICATION, VERIFIED, REJECTED
    verification_status = db.Column(db.String(30), default="PENDING VERIFICATION")
    # Role: SUPER_ADMIN, ADMIN, HR, EMPLOYEE
    uploaded_by_role = db.Column(db.String(20), default="EMPLOYEE")
    
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default="Active") # Active, Inactive
    
    last_viewed_at = db.Column(db.DateTime, nullable=True) # Last viewed by any user
    view_count = db.Column(db.Integer, default=0) # Total number of times viewed/downloaded

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