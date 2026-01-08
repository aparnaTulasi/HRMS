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
    return jsonify({
        'id': emp.id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'department': emp.department,
        'designation': emp.designation,
        'phone': emp.work_phone,
        'date_of_joining': emp.date_of_joining
    })

# Other employee routes like /bank, /address etc. would go here