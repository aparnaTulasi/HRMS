from flask import Blueprint, request, jsonify
from utils.email_validator import validate_email
from utils.otp import generate_otp
from models import db
from models.otp import EmployeeOTP

employee_routes_bp = Blueprint('employee_routes', __name__)

@employee_routes_bp.route("/signup", methods=["POST"])
def employee_signup():
    data = request.json
    email = data.get("email")
    # password = data.get("password") # Password logic to be handled upon approval or stored temporarily

    is_valid, msg = validate_email(email)
    if not is_valid:
        return jsonify({"error": msg}), 400

    otp = generate_otp()

    # Check if OTP entry exists for this email, otherwise create new
    otp_entry = EmployeeOTP.query.filter_by(email=email, status="PENDING").first()
    if not otp_entry:
        otp_entry = EmployeeOTP(
            email=email,
            otp=otp,
            status="PENDING"
        )
        db.session.add(otp_entry)
    else:
        otp_entry.otp = otp # Update OTP if retrying
        
    db.session.commit()

    # In production, send this via SMTP
    print(f"OTP for {email}: {otp}")

    return jsonify({
        "message": "OTP sent to email",
        "status": "PENDING"
    }), 201

@employee_routes_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    email = data.get("email")
    otp = data.get("otp")

    record = EmployeeOTP.query.filter_by(
        email=email,
        otp=otp,
        status="PENDING"
    ).first()

    if not record:
        return jsonify({"error": "Invalid OTP"}), 400

    record.status = "VERIFIED"
    db.session.commit()

    return jsonify({
        "message": "OTP verified, waiting for admin approval",
        "status": "PENDING_APPROVAL"
    }), 200