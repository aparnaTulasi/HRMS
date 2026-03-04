from datetime import datetime, timedelta
from flask_login import UserMixin
from models import db
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)  # company_email (sync)
    phone = db.Column(db.String(20), nullable=True)    # phone_number (sync)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')

    # ✅ NEW FLAGS
    profile_completed = db.Column(db.Boolean, default=False)
    profile_locked = db.Column(db.Boolean, default=False)

    portal_prefix = db.Column(db.String(50), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee_profile = db.relationship('Employee', backref='user', uselist=False, lazy=True)
    permissions = db.relationship('UserPermission', foreign_keys='UserPermission.user_id', backref=db.backref('user', foreign_keys='UserPermission.user_id'), lazy=True)

    __table_args__ = (db.UniqueConstraint('company_id', 'email', name='unique_company_email'),)
    def generate_otp(self):
        self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return self.otp

    def has_permission(self, permission_code):
        if self.role == 'SUPER_ADMIN':
            return True
        return any(p.permission_code == permission_code for p in self.permissions)