from flask import Blueprint, jsonify, g, request
from models import db
from models.profile_change_request import ProfileChangeRequest
from models.profile_change_request_item import ProfileChangeRequestItem
from models.employee import Employee
from models.super_admin import SuperAdmin
from models.employee_address import EmployeeAddress
from models.notification import Notification
from constants.profile_fields import ROLE_ESCALATION
from utils.decorators import token_required, role_required
from datetime import datetime

profile_approval_bp = Blueprint('profile_approval', __name__)

def create_notification(user_id, role, message):
    notif = Notification(user_id=user_id, role=role, message=message)
    db.session.add(notif)

@profile_approval_bp.route('/api/approvals/profile-changes', methods=['GET'])
@token_required
@role_required(['HR', 'ADMIN', 'SUPER_ADMIN', 'ROOT_ADMIN'])
def list_pending_profile_requests():
    requests = ProfileChangeRequest.query.filter_by(
        current_approver_role=g.user.role
    ).filter(ProfileChangeRequest.status.in_(['PENDING', 'ESCALATED'])).all()

    results = []
    for req in requests:
        items = [{
            "field_name": item.field_name,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "model": item.model_name
        } for item in req.items]
        
        results.append({
            "id": req.id,
            "requester_id": req.requester_user_id,
            "requested_by_role": req.requested_by_role,
            "status": req.status,
            "reason": req.reason,
            "created_at": req.created_at.isoformat(),
            "items": items
        })
    
    return jsonify({"success": True, "data": results}), 200

@profile_approval_bp.route('/api/approvals/profile-changes/<int:req_id>/approve', methods=['POST'])
@token_required
@role_required(['HR', 'ADMIN', 'SUPER_ADMIN', 'ROOT_ADMIN'])
def approve_profile_request(req_id):
    req_obj = ProfileChangeRequest.query.get_or_404(req_id)
    
    if req_obj.status not in ['PENDING', 'ESCALATED']:
        return jsonify({"message": f"Request is already {req_obj.status}"}), 400
    
    if req_obj.current_approver_role != g.user.role:
        return jsonify({"message": "Not authorized to approve at this stage"}), 403

    try:
        next_role = ROLE_ESCALATION.get(g.user.role)
        
        if next_role:
            # Escalate
            req_obj.status = 'ESCALATED'
            req_obj.current_approver_role = next_role
            create_notification(None, next_role, f"New profile correction request escalated from {g.user.role}")
            message = f"Request approved by {g.user.role} and escalated to {next_role}."
        else:
            # Final Approval -> Apply Changes
            req_obj.status = 'APPROVED' # Intermediate state before APPLIED
            db.session.flush()

            # Apply using row-level locking
            for item in req_obj.items:
                if item.model_name == "Employee":
                    target = db.session.query(Employee).filter_by(user_id=req_obj.target_user_id).with_for_update().first()
                elif item.model_name == "SuperAdmin":
                    target = db.session.query(SuperAdmin).filter_by(user_id=req_obj.target_user_id).with_for_update().first()
                elif item.model_name == "EmployeeAddress":
                    emp = Employee.query.filter_by(user_id=req_obj.target_user_id).first()
                    if not emp.address:
                        emp.address = EmployeeAddress(employee_id=emp.id)
                        db.session.add(emp.address)
                    target = db.session.query(EmployeeAddress).filter_by(id=emp.address.id).with_for_update().first()
                else:
                    target = None
                
                if target:
                    val = item.new_value
                    # Basic type conversion for numbers if needed (but profile fields are mostly string/text)
                    setattr(target, item.field_key, val)
            
            req_obj.status = 'APPLIED'
            req_obj.applied_at = datetime.utcnow()
            req_obj.decided_at = datetime.utcnow()
            create_notification(req_obj.requester_user_id, None, "Your profile correction request has been finalized and applied.")
            message = "Profile corrections successfully applied."

        db.session.commit()
        return jsonify({"success": True, "message": message}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@profile_approval_bp.route('/api/approvals/profile-changes/<int:req_id>/reject', methods=['POST'])
@token_required
@role_required(['HR', 'ADMIN', 'SUPER_ADMIN', 'ROOT_ADMIN'])
def reject_profile_request(req_id):
    req_obj = ProfileChangeRequest.query.get_or_404(req_id)
    
    if req_obj.status not in ['PENDING', 'ESCALATED']:
        return jsonify({"message": f"Request is already {req_obj.status}"}), 400
    
    if req_obj.current_approver_role != g.user.role:
        return jsonify({"message": "Not authorized to reject at this stage"}), 403

    req_obj.status = 'REJECTED'
    req_obj.decided_at = datetime.utcnow()
    
    create_notification(req_obj.requester_user_id, None, f"Your profile correction request was rejected by {g.user.role}.")
    
    db.session.commit()
    return jsonify({"success": True, "message": "Request rejected."}), 200
