from flask import Blueprint, request, jsonify
from models import db
from models.user import User
from datetime import datetime, timedelta
import secrets
import string
from utils.email_utils import send_otp_email

otp_bp = Blueprint('otp', __name__)

@otp_bp.route('/request', methods=['POST'])
def request_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Generate 6-digit OTP
    otp = ''.join(secrets.choice(string.digits) for _ in range(6))
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    # Update User record
    user.otp = otp
    user.otp_expiry = otp_expiry
    db.session.commit()

    # Send Email
    if send_otp_email(email, otp):
        return jsonify({"message": "OTP sent successfully to your email."}), 200
    else:
        return jsonify({"error": "Failed to send OTP email."}), 500