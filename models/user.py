from datetime import datetime, timedelta
from flask_login import UserMixin
from models import db
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='EMPLOYEE')
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_superadmin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee_profile = db.relationship('Employee', backref='user', foreign_keys='Employee.user_id', uselist=False)

    def __repr__(self):
        return f'<User {self.email}>'

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