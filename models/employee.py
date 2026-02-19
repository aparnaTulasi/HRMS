from datetime import datetime
from models import db

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.String(50), unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    company_email = db.Column(db.String(120))
    personal_email = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    department = db.Column(db.String(50))
    designation = db.Column(db.String(50))
    date_of_joining = db.Column(db.Date)
    employment_type = db.Column(db.String(50))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    pay_grade = db.Column(db.String(50))
    ctc = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bank_details = db.relationship('EmployeeBankDetails', backref='employee', uselist=False, lazy=True)
    address = db.relationship('EmployeeAddress', backref='employee', uselist=False, lazy=True)
    documents = db.relationship('EmployeeDocument', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
    manager = db.relationship('Employee', remote_side=[id], backref='subordinates')