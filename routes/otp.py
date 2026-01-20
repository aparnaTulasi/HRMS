from flask import Blueprint, jsonify

otp_bp = Blueprint('otp', __name__)

@otp_bp.route('/', methods=['GET'])
def otp_index():
    return jsonify({"message": "OTP API is running"})