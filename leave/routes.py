from flask import request, jsonify, g
from utils.decorators import token_required, role_required
from . import leave_bp
from .models import LeaveRequest
from models import db
from models.employee import Employee
from datetime import datetime

@leave_bp.route('/apply', methods=['POST'])
@token_required
def apply_leave():
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404

    new_leave = LeaveRequest(
        employee_id=emp.id,
        company_id=emp.company_id,
        leave_type_id=data['leave_type_id'],
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
        reason=data['reason']
    )
    db.session.add(new_leave)
    db.session.commit()
    return jsonify({'message': 'Leave application submitted'}), 201

@leave_bp.route('/<int:id>/approve', methods=['POST'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def approve_leave(id):
    leave = LeaveRequest.query.get_or_404(id)
    
    approver_emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    data = request.get_json()
    leave.status = data.get('status', 'Approved')
    leave.approved_by = approver_emp.id if approver_emp else None
    db.session.commit()
    return jsonify({'message': f'Leave {leave.status.lower()}'})