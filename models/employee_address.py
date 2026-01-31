from models import db
from datetime import datetime

class EmployeeAddress(db.Model):
    __tablename__ = 'employee_address'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    address_type = db.Column(db.String(20)) # PRESENT / PERMANENT
    address_line1 = db.Column(db.String(150))
    address_line2 = db.Column(db.String(150))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)