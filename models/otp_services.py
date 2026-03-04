import random
import string
from datetime import datetime, timedelta

class OTPService:
    @staticmethod
    def generate_otp(length=6):
        """Generate a numeric OTP of specified length."""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def get_expiry(minutes=10):
        """Get the expiry datetime for the OTP."""
        return datetime.utcnow() + timedelta(minutes=minutes)