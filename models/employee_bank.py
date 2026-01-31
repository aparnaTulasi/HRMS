from models import db
from datetime import datetime

class EmployeeBankDetails(db.Model):
    __tablename__ = 'employee_bank_details'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), unique=True, nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    branch_name= db.Column(db.String(100),nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    ifsc_code = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)