from datetime import datetime, timedelta
from flask_login import UserMixin
from models import db
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE') # Kept for backward compatibility
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_superadmin = db.Column(db.Boolean, default=False)
    is_hr = db.Column(db.Boolean, default=False)
    portal_prefix = db.Column(db.String(50), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee_profile = db.relationship('Employee', backref='user', uselist=False, lazy=True)
    
    # Explicitly specify foreign_keys for permissions relationship
    permissions = db.relationship(
        'UserPermission', 
        foreign_keys='UserPermission.user_id', 
        backref='user', 
        lazy=True
    )

    def generate_otp(self):
        if self.role == 'EMPLOYEE':
            self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
            self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            return self.otp
        return None

    def has_permission(self, permission_code):
        if self.role == 'SUPER_ADMIN':
            return True
        return any(p.permission_code == permission_code for p in self.permissions)