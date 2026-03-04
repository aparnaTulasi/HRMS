from flask import Blueprint, request, jsonify, g
from models import db
from models.employee import Employee
from utils.decorators import token_required
from datetime import datetime

employee_advanced_bp = Blueprint('employee_advanced', __name__)

@employee_advanced_bp.route('/education', methods=['POST'])
@token_required
def add_education():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID is required'}), 400
    
    emp = Employee.query.get(emp_id)
    if not emp: return jsonify({'message': 'Employee not found'}), 404

    # The payload is expected to be a list of education objects
    emp.education_details = data.get('education_details')
    db.session.commit()
    return jsonify({'message': 'Education details updated successfully'})

@employee_advanced_bp.route('/experience', methods=['POST'])
@token_required
def add_experience():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID is required'}), 400
    
    emp = Employee.query.get(emp_id)
    if not emp: return jsonify({'message': 'Employee not found'}), 404

    # The payload is expected to be a list of experience objects
    emp.previous_employment = data.get('previous_employment')
    db.session.commit()
    return jsonify({'message': 'Experience details updated successfully'})

@employee_advanced_bp.route('/other', methods=['POST'])
@token_required
def add_other_details():
    data = request.get_json()
    emp_id = data.get('employee_id') if g.user.role in ['ADMIN', 'HR'] else g.user.employee_profile.id
    if not emp_id: return jsonify({'message': 'Employee ID required'}), 400
    
    emp = Employee.query.get(emp_id)
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    
    if 'uan_number' in data: emp.uan_number = data['uan_number']
    if 'pf_number' in data: emp.pf_number = data['pf_number']
    if 'esic_number' in data: emp.esic_number = data['esic_number']
    
    db.session.commit()
    return jsonify({'message': 'Other details updated'})