from datetime import datetime, timedelta
from models import db
import secrets

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.String(20), default='PENDING') # ACTIVE, PENDING
    portal_prefix = db.Column(db.String(50), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee_profile = db.relationship('Employee', backref='user', uselist=False, lazy=True)

    def generate_otp(self):
        """Generate 6-digit OTP"""
        self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return self.otp