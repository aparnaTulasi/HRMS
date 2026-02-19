from flask import Blueprint, jsonify, request, g
from datetime import datetime
from models import db
from models.user import User
from models.employee import Employee
from models.employee_onboarding_request import EmployeeOnboardingRequest
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
            'full_name': emp.full_name,
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

@hr_bp.route('/onboarding-request', methods=['POST'])
@token_required
@role_required(['HR'])
def create_onboarding_request():
    data = request.get_json(force=True)

    req = EmployeeOnboardingRequest(
        company_id=g.user.company_id,
        requested_by=g.user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        personal_email=data['personal_email'],
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=datetime.strptime(data['date_of_joining'], '%Y-%m-%d').date() if data.get('date_of_joining') else None,
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({"message": "Onboarding request created", "request_id": req.id}), 201