from flask import Blueprint, request, jsonify
from models import db
from models.user import User
from datetime import datetime

verify_bp = Blueprint('verify', __name__)

@verify_bp.route('/otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.otp != otp:
        return jsonify({"error": "Invalid OTP"}), 400
        
    if user.otp_expiry and datetime.utcnow() > user.otp_expiry:
        return jsonify({"error": "OTP has expired"}), 400

    # Activate User
    user.status = "ACTIVE"
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({"message": "Account verified successfully. You can now login."}), 200