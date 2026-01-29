from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocument
from utils.decorators import token_required
import os
from config import Config
from werkzeug.utils import secure_filename

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Profile not found'}), 404
    
    addresses = []
    for addr in emp.addresses:
        addresses.append({
            'type': addr.address_type,
            'line1': addr.address_line1,
            'line2': addr.address_line2,
            'city': addr.city,
            'state': addr.state,
            'zip_code': addr.zip_code,
            'country': addr.country
        })

    return jsonify({
        'id': emp.id,
        'employee_id': emp.employee_id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'email': emp.company_email,
        'personal_email': emp.personal_email,
        'department': emp.department,
        'designation': emp.designation,
        'salary': emp.salary,
        'phone': getattr(emp, 'work_phone', None),
        'date_of_joining': emp.date_of_joining.isoformat() if emp.date_of_joining else None,
        'addresses': addresses
    })

# Other employee routes like /bank, /address etc. would go here