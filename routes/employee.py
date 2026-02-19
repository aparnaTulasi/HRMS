from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocument
from models.user import User
from utils.decorators import token_required, role_required
import os
from config import Config
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from datetime import datetime

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/me/profile', methods=['GET'])
@token_required
def me_profile():
    emp = Employee.query.filter_by(
        user_id=g.user.id,
        company_id=g.user.company_id
    ).first()

    if not emp:
        return jsonify({'success': False, 'message': 'Profile not found'}), 404

    return jsonify({
        "success": True,
        "data": {
            "basic_details": {
                "full_name": emp.full_name,
                "personal_email": getattr(emp, 'personal_email', None),
                "company_email": getattr(emp, 'company_email', g.user.email)
            },
            "user": {
                "id": g.user.id,
                "role": g.user.role,
                "account_status": g.user.status,
                "company_email": getattr(emp, 'company_email', g.user.email),
                "phone_number": getattr(emp, 'phone_number', getattr(emp, 'work_phone', None))
            },
            "work_information": {
                "employee_id": emp.employee_id,
                "department": emp.department,
                "role_designation": emp.designation,
                "manager_reporting_to": getattr(emp, 'manager_id', None),
                "date_of_joining": emp.date_of_joining.isoformat() if emp.date_of_joining else "",
                "branch_location": None
            }
        }
    })

@employee_bp.route('/me/profile/save', methods=['POST'])
@token_required
def save_profile():
    data = request.get_json() or {}

    emp = Employee.query.filter_by(
        user_id=g.user.id,
        company_id=g.user.company_id
    ).first()

    if not emp:
        return jsonify({'success': False, 'message': 'Profile not found'}), 404

    # ✅ IF PROFILE LOCKED → create request (later we expand)
    if g.user.profile_locked:
        # For now just block and simulate request creation
        return jsonify({
            "success": False,
            "code": "PROFILE_LOCKED",
            "message": "No access. Change request must be submitted."
        }), 403

    # ✅ FIRST TIME SAVE (DIRECT UPDATE)

    if "full_name" in data:
        emp.full_name = data["full_name"]

    if "personal_email" in data:
        emp.personal_email = data["personal_email"]

    if "company_email" in data:
        emp.company_email = data["company_email"]
        g.user.email = data["company_email"]   # sync login email

    if "phone_number" in data:
        emp.phone_number = data["phone_number"]

    if "department" in data:
        emp.department = data["department"]

    if "designation" in data:
        emp.designation = data["designation"]

    if "date_of_joining" in data and data["date_of_joining"]:
        emp.date_of_joining = datetime.strptime(
            data["date_of_joining"], "%Y-%m-%d"
        ).date()

    # 🔒 LOCK PROFILE
    g.user.profile_completed = True
    g.user.profile_locked = True

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Profile saved and locked successfully."
    })

@employee_bp.route('/address', methods=['POST'])
@token_required
def add_address():
    data = request.get_json()
    
    if g.user.role in ['ADMIN', 'HR', 'SUPER_ADMIN']:
        emp_id = data.get('employee_id')
        if not emp_id:
            return jsonify({'message': 'Employee ID required'}), 400
    else:
        if not g.user.employee_profile:
            return jsonify({'message': 'Profile not found'}), 404
        emp_id = g.user.employee_profile.id

    emp = Employee.query.get(emp_id)
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404
        
    if g.user.role != 'SUPER_ADMIN' and emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized access'}), 403

    address = EmployeeAddress.query.filter_by(employee_id=emp_id).first()
    if not address:
        address = EmployeeAddress(employee_id=emp_id)
        db.session.add(address)
        
    address.address_line1 = data.get('address_line1')
    address.permanent_address = data.get('permanent_address')
    address.city = data.get('city')
    address.state = data.get('state')
    address.zip_code = data.get('zip_code')
    
    db.session.commit()
    return jsonify({'message': 'Address updated successfully'})

@employee_bp.route('/bank', methods=['POST'])
@token_required
def add_bank_details():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID required'}), 400
    
    emp = Employee.query.get(emp_id)
    if not emp or emp.company_id != g.user.company_id:
        return jsonify({'message': 'Employee not found or unauthorized'}), 404

    bank = EmployeeBankDetails.query.filter_by(employee_id=emp_id).first() or EmployeeBankDetails(employee_id=emp_id)
    if not bank.id: db.session.add(bank)
    
    bank.bank_name = data.get('bank_name')
    bank.account_number = data.get('account_number')
    bank.ifsc_code = data.get('ifsc_code')
    bank.branch_name = data.get('branch_name')
    
    # Update Statutory details on Employee model
    if 'pan_number' in data: emp.pan_number = data['pan_number']
    if 'aadhaar_number' in data: emp.aadhaar_number = data['aadhaar_number']
    
    db.session.commit()
    return jsonify({'message': 'Bank and statutory details updated successfully'})