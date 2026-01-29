from datetime import datetime
from models import db

class Payslip(db.Model):
    __tablename__ = 'payslips'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_earnings = db.Column(db.Float, nullable=False)
    total_deductions = db.Column(db.Float, nullable=False)
    net_salary = db.Column(db.Float, nullable=False)
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_mime = db.Column(db.String(100), default='application/pdf')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)