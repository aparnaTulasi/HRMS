from datetime import datetime
from models import db

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    company_code = db.Column(db.String(20))
    employee_id = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    father_or_husband_name = db.Column(db.String(100))
    mother_name = db.Column(db.String(100))
    department = db.Column(db.String(50))
    designation = db.Column(db.String(50))
    salary = db.Column(db.Float(10,2))
    date_of_joining = db.Column(db.Date)
    work_phone = db.Column(db.String(20))
    personal_mobile = db.Column(db.String(20))
    personal_email = db.Column(db.String(120))
    company_email = db.Column(db.String(120))
    work_mode = db.Column(db.String(20))
    branch_id = db.Column(db.Integer)
    aadhaar_number = db.Column(db.String(20), unique=True)
    pan_number = db.Column(db.String(20), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bank_details = db.relationship('EmployeeBankDetails', backref='employee', uselist=False, lazy=True)
    addresses = db.relationship('EmployeeAddress', backref='employee', lazy=True)
    documents = db.relationship('EmployeeDocument', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)


    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"