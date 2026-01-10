from datetime import datetime
from models import db

class EmployeeOTP(db.Model):
    __tablename__ = 'employee_otps'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    status = db.Column(db.String(20), default="PENDING")  # PENDING, VERIFIED, APPROVED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<EmployeeOTP {self.email} - {self.status}>'