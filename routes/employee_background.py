from flask import Blueprint, request, jsonify, g
from models import db
from models.employee_education import EmployeeEducation
from models.employee_work_experience import EmployeeWorkExperience
from models.employee import Employee
from utils.decorators import token_required
from datetime import datetime

employee_bg_bp = Blueprint('employee_background', __name__)

def _get_employee():
    return Employee.query.filter_by(user_id=g.user.id).first()

@employee_bg_bp.route('/api/me/education', methods=['GET'])
@token_required
def get_my_education():
    emp = _get_employee()
    if not emp:
        return jsonify({"success": False, "message": "Employee record not found"}), 404
    
    education = EmployeeEducation.query.filter_by(employee_id=emp.id).all()
    return jsonify({"success": True, "data": [e.to_dict() for e in education]})

@employee_bg_bp.route('/api/me/education', methods=['POST'])
@token_required
def add_my_education():
    emp = _get_employee()
    if not emp:
        return jsonify({"success": False, "message": "Employee record not found"}), 404
    
    data = request.get_json()
    if not all(k in data for k in ['institution', 'degree']):
        return jsonify({"success": False, "message": "Institution and Degree are required"}), 400
    
    edu = EmployeeEducation(
        employee_id=emp.id,
        institution=data['institution'],
        degree=data['degree'],
        field_of_study=data.get('field_of_study'),
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
        percentage=data.get('percentage')
    )
    db.session.add(edu)
    db.session.commit()
    return jsonify({"success": True, "message": "Education added successfully", "data": edu.to_dict()}), 201

@employee_bg_bp.route('/api/me/education/<int:edu_id>', methods=['DELETE'])
@token_required
def delete_my_education(edu_id):
    emp = _get_employee()
    edu = EmployeeEducation.query.filter_by(id=edu_id, employee_id=emp.id).first()
    if not edu:
        return jsonify({"success": False, "message": "Record not found"}), 404
    
    db.session.delete(edu)
    db.session.commit()
    return jsonify({"success": True, "message": "Education deleted successfully"})

@employee_bg_bp.route('/api/me/experience', methods=['GET'])
@token_required
def get_my_experience():
    emp = _get_employee()
    if not emp:
        return jsonify({"success": False, "message": "Employee record not found"}), 404
    
    experience = EmployeeWorkExperience.query.filter_by(employee_id=emp.id).all()
    return jsonify({"success": True, "data": [e.to_dict() for e in experience]})

@employee_bg_bp.route('/api/me/experience', methods=['POST'])
@token_required
def add_my_experience():
    emp = _get_employee()
    if not emp:
        return jsonify({"success": False, "message": "Employee record not found"}), 404
    
    data = request.get_json()
    if not all(k in data for k in ['company_name', 'designation']):
        return jsonify({"success": False, "message": "Company and Designation are required"}), 400
    
    exp = EmployeeWorkExperience(
        employee_id=emp.id,
        company_name=data['company_name'],
        designation=data['designation'],
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
        description=data.get('description')
    )
    db.session.add(exp)
    db.session.commit()
    return jsonify({"success": True, "message": "Experience added successfully", "data": exp.to_dict()}), 201

@employee_bg_bp.route('/api/me/experience/<int:exp_id>', methods=['DELETE'])
@token_required
def delete_my_experience(exp_id):
    emp = _get_employee()
    exp = EmployeeWorkExperience.query.filter_by(id=exp_id, employee_id=emp.id).first()
    if not exp:
        return jsonify({"success": False, "message": "Record not found"}), 404
    
    db.session.delete(exp)
    db.session.commit()
    return jsonify({"success": True, "message": "Experience deleted successfully"})
