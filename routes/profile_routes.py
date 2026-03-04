from flask import Blueprint, jsonify, g
from models import db
from models.user import User
from models.employee import Employee
from utils.decorators import token_required
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/api/me/profile', methods=['GET'])
@token_required
def my_profile_ui():
    emp = Employee.query.filter_by(user_id=g.user.id, company_id=g.user.company_id).first()
    if not emp:
        return jsonify({'message': 'Profile not found'}), 404

    # Using model fields from context. This is robust even if fields are missing.
    return jsonify({
        "success": True,
        "data": {
            "user": {
                "id": g.user.id,
                "role": g.user.role,
                "account_status": g.user.status,
                "profile_completed": getattr(g.user, "profile_completed", False),
                "profile_locked": getattr(g.user, "profile_locked", False),

                # The Employee model has no `company_email`, so we use the User's email.
                # The model has `work_phone`, not `phone_number`.
                "company_email": g.user.email,
                "phone_number": getattr(emp, 'work_phone', None)
            },
            "work_information": {
                "employee_id": emp.employee_id,
                "department": emp.department,
                "role_designation": emp.designation,
                "manager_reporting_to": getattr(emp, 'manager_id', None),
                "date_of_joining": emp.date_of_joining.isoformat() if emp.date_of_joining else "",
                "branch_location": None
            },
            "basic_details": {
                "full_name": emp.full_name,
                "personal_email": emp.personal_email
            }
        }
    })