from models import db
from datetime import datetime

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(50))
    designation = db.Column(db.String(50))
    date_of_joining = db.Column(db.String(20))
    salary = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    bank_details = db.relationship('EmployeeBankDetails', backref='employee', uselist=False, lazy=True)
    address = db.relationship('EmployeeAddress', backref='employee', uselist=False, lazy=True)
    documents = db.relationship('EmployeeDocuments', backref='employee', lazy=True)