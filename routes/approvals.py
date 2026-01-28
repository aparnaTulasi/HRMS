from flask import Blueprint, request, jsonify, g
from models import db
from models.approvals import ApprovalRequest, ApprovalStep, ApprovalAction
from models.user import User
from utils.decorators import token_required
from datetime import datetime

approvals_bp = Blueprint('approvals', __name__)

@approvals_bp.route('/create', methods=['POST'])
@token_required
def create_approval_request():
    """
    Internal API to start a workflow.
    Expected JSON:
    {
        "request_type": "LEAVE",
        "resource_id": 123,
        "steps": [
            {"name": "Manager Approval", "role": "MANAGER", "order": 1},
            {"name": "HR Approval", "role": "HR", "order": 2}
        ]
    }
    """
    data = request.get_json()
    
    # Create Request
    new_req = ApprovalRequest(
        request_type=data['request_type'],
        resource_id=data['resource_id'],
        requester_id=g.user.id,
        status='PENDING',
        current_step_order=1
    )
    db.session.add(new_req)
    db.session.flush() # Get ID
    
    # Create Steps
    for step_data in data.get('steps', []):
        step = ApprovalStep(
            request_id=new_req.id,
            step_name=step_data['name'],
            step_order=step_data['order'],
            role_required=step_data.get('role'),
            specific_user_id=step_data.get('user_id')
        )
        db.session.add(step)
        
    db.session.commit()
    return jsonify({'message': 'Approval workflow initiated', 'request_id': new_req.id}), 201

@approvals_bp.route('/pending', methods=['GET'])
@token_required
def get_pending_approvals():
    """Get requests waiting for current user's action"""
    # Get all pending steps
    pending_steps = ApprovalStep.query.filter_by(status='PENDING').all()
    
    my_pending = []
    for step in pending_steps:
        # Check if this step belongs to the active request step order
        req = ApprovalRequest.query.get(step.request_id)
        if req.status != 'PENDING' or req.current_step_order != step.step_order:
            continue
            
        # Check permissions
        authorized = False
        if step.specific_user_id and step.specific_user_id == g.user.id:
            authorized = True
        elif step.role_required and step.role_required == g.user.role:
            authorized = True
        # Note: For MANAGER role, you might want to add logic to check if user is manager of requester
            
        if authorized:
            my_pending.append({
                'request_id': req.id,
                'type': req.request_type,
                'resource_id': req.resource_id,
                'step_name': step.step_name,
                'created_at': req.created_at
            })
            
    return jsonify(my_pending)

@approvals_bp.route('/<int:req_id>/action', methods=['POST'])
@token_required
def approval_action(req_id):
    """
    Approve or Reject
    { "action": "APPROVE", "comments": "Looks good" }
    """
    data = request.get_json()
    action_type = data.get('action') # APPROVE / REJECT
    comments = data.get('comments')
    
    req = ApprovalRequest.query.get_or_404(req_id)
    
    if req.status != 'PENDING':
        return jsonify({'message': 'Request is already closed'}), 400
        
    # Find current step
    current_step = ApprovalStep.query.filter_by(
        request_id=req.id, 
        step_order=req.current_step_order
    ).first()
    
    if not current_step:
        return jsonify({'message': 'Configuration error: No step found'}), 500
        
    # Authorization Check
    authorized = False
    if current_step.specific_user_id == g.user.id:
        authorized = True
    elif current_step.role_required == g.user.role:
        authorized = True
        
    if not authorized:
        return jsonify({'message': 'You are not authorized to perform this action'}), 403
        
    # Record Action
    log = ApprovalAction(
        request_id=req.id,
        step_id=current_step.id,
        actor_id=g.user.id,
        action=action_type,
        comments=comments
    )
    db.session.add(log)
    
    if action_type == 'APPROVE':
        current_step.status = 'APPROVED'
        
        # Check if there is a next step
        next_step = ApprovalStep.query.filter_by(
            request_id=req.id, 
            step_order=req.current_step_order + 1
        ).first()
        
        if next_step:
            req.current_step_order += 1
        else:
            req.status = 'APPROVED'
            # TODO: Trigger callback to update actual resource (Leave/Expense) status
            
    elif action_type == 'REJECT':
        current_step.status = 'REJECTED'
        req.status = 'REJECTED'
        
    db.session.commit()
    return jsonify({'message': f'Request {action_type}D successfully'})

@approvals_bp.route('/<int:req_id>/history', methods=['GET'])
@token_required
def approval_history(req_id):
    req = ApprovalRequest.query.get_or_404(req_id)
    
    # Allow requester or admins/approvers to view
    if req.requester_id != g.user.id and g.user.role not in ['ADMIN', 'HR', 'MANAGER']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    history = []
    for action in req.actions:
        actor = User.query.get(action.actor_id)
        history.append({
            'action': action.action,
            'actor': actor.email if actor else 'Unknown',
            'comments': action.comments,
            'date': action.performed_at
        })
        
    return jsonify({
        'request_status': req.status,
        'current_step': req.current_step_order,
        'history': history
    })