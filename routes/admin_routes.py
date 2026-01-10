from flask import Blueprint, jsonify
from models import db
from models.otp import EmployeeOTP
from models.user import User 
from utils.decorators import role_required
from werkzeug.security import generate_password_hash

admin_routes_bp = Blueprint('admin_routes', __name__)

@admin_routes_bp.route("/approve-employee/<int:otp_id>", methods=["PUT"])
@role_required(['ADMIN'])
def approve_employee(otp_id):
    otp_record = EmployeeOTP.query.get_or_404(otp_id)
    
    if otp_record.status != "VERIFIED":
        return jsonify({"error": "Employee OTP is not in VERIFIED state"}), 400

    otp_record.status = "APPROVED"

    # Create the actual User record
    # Note: Setting a default password or handling password from signup is required here
    default_password = generate_password_hash("Welcome@123", method='pbkdf2:sha256')
    
    employee = User(
        email=otp_record.email,
        password=default_password,
        role="EMPLOYEE",
        is_active=True
    )

    db.session.add(employee)
    db.session.commit()

    return jsonify({
        "message": "Employee approved successfully"
    }), 200