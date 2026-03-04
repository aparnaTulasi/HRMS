from datetime import datetime, timedelta
import secrets, string
from models import db

class SuperAdmin(db.Model):
    __tablename__ = "super_admins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))

    is_verified = db.Column(db.Boolean, default=False)

    signup_otp = db.Column(db.String(6))
    signup_otp_expiry = db.Column(db.DateTime)

    reset_otp = db.Column(db.String(6), nullable=True)
    reset_otp_expiry = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('super_admin', uselist=False))

    def generate_signup_otp(self):
        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        self.signup_otp = otp
        self.signup_otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return otp

    def generate_reset_otp(self):
        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        self.reset_otp = otp
        self.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return otp
