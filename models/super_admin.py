from datetime import datetime, timedelta
import secrets
import string
from models import db

class SuperAdmin(db.Model):
    __tablename__ = "super_admins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))

    email = db.Column(db.String(120))

    password = db.Column(db.String(255))
    confirm_password = db.Column(db.String(255))

    reset_otp = db.Column(db.String(10), nullable=True)
    reset_otp_expiry = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to User
    user = db.relationship("User", backref=db.backref("super_admin_profile", uselist=False))

    def generate_reset_otp(self):
        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        self.reset_otp = otp
        self.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return otp
