from flask import Blueprint, request, jsonify, g
from models import db
from models.exit import ExitRequest
from models.employee import Employee
from utils.decorators import token_required, role_required
from datetime import datetime

exit_bp = Blueprint('exit', __name__)

@exit_bp.route('/apply', methods=['POST'])
@token_required
def apply_resignation():
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    if not emp:
        return jsonify({"message": "Employee profile not found"}), 404
        
    if not data.get('desired_lwd') or not data.get('reason'):
        return jsonify({"message": "Desired Last Working Day and Reason are required"}), 400
        
    try:
        lwd = datetime.strptime(data['desired_lwd'], '%Y-%m-%d')
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400
        
    # Check if a request already exists
    existing = ExitRequest.query.filter_by(employee_id=emp.id, status='PENDING').first()
    if existing:
        return jsonify({"message": "You already have a pending resignation request"}), 400
        
    new_request = ExitRequest(
        employee_id=emp.id,
        company_id=emp.company_id,
        desired_lwd=lwd,
        reason=data['reason']
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Resignation request submitted successfully",
        "request_id": new_request.id
    }), 201

@exit_bp.route('/requests', methods=['GET'])
@token_required
@role_required(['HR', 'ADMIN', 'SUPER_ADMIN'])
def get_exit_requests():
    q = ExitRequest.query
    if g.user.role != 'SUPER_ADMIN':
        q = q.filter_by(company_id=g.user.company_id)
        
    requests = q.order_by(ExitRequest.resignation_date.desc()).all()
    
    return jsonify({
        "success": True,
        "requests": [r.to_dict() for r in requests]
    })

@exit_bp.route('/approve-reject', methods=['PUT'])
@token_required
@role_required(['HR', 'ADMIN', 'SUPER_ADMIN'])
def approve_reject_exit():
    data = request.get_json()
    req_id = data.get('id')
    status = data.get('status') # APPROVED, REJECTED, COMPLETED
    
    if not req_id or not status:
        return jsonify({"message": "ID and Status are required"}), 400
        
    req = ExitRequest.query.get(req_id)
    if not req:
        return jsonify({"message": "Request not found"}), 404
        
    if g.user.role != 'SUPER_ADMIN' and req.company_id != g.user.company_id:
        return jsonify({"message": "Permission denied"}), 403
        
    req.status = status
    req.hr_remarks = data.get('remarks')
    
    if status == 'APPROVED' and data.get('official_lwd'):
        req.official_lwd = datetime.strptime(data['official_lwd'], '%Y-%m-%d')
        
    # If COMPLETED, de-activate the employee record
    if status == 'COMPLETED':
        emp = Employee.query.get(req.employee_id)
        if emp:
            emp.status = 'EXITED'
            emp.is_active = False
            
    db.session.commit()
    return jsonify({"success": True, "message": f"Request {status} successfully"})
