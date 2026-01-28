from flask import Blueprint, jsonify, request, g
from models import db
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required

hr_bp = Blueprint('hr', __name__)

@hr_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    output = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        output.append({
            'id': emp.id,
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'email': user.email,
            'status': user.status,
            'department': emp.department,
            'designation': emp.designation
        })
    return jsonify({'employees': output})

@hr_bp.route('/approve-employee/<int:user_id>', methods=['POST'])
@token_required
@role_required(['HR'])
def approve_employee(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    if user.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized access'}), 403
    user.status = 'ACTIVE'
    db.session.commit()
    return jsonify({'message': 'Employee approved successfully', 'status': 'ACTIVE'})

@hr_bp.route('/team', methods=['GET'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def get_team():
    query = Employee.query.filter_by(company_id=g.user.company_id)
    
    # If Manager, filter by department (assuming Manager manages their department)
    if g.user.role == 'MANAGER':
        manager_emp = Employee.query.filter_by(user_id=g.user.id).first()
        if manager_emp and manager_emp.department:
            query = query.filter_by(department=manager_emp.department)
            
    employees = query.all()
    output = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        output.append({
            'id': emp.id,
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'email': user.email if user else "",
            'department': emp.department,
            'designation': emp.designation
        })
    return jsonify(output)