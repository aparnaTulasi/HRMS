from flask import Blueprint, request, jsonify, g
from models import db
from models.approvals import ApprovalRequest, ApprovalStep, ApprovalAction
from utils.decorators import token_required, role_required
from datetime import datetime, timedelta
from leave.models import LeaveRequest

def _date(d):
    return datetime.strptime(d, "%Y-%m-%d").date()

def _next_day(date_obj):
    return date_obj + timedelta(days=1)

approvals_bp = Blueprint("approvals", __name__)

@approvals_bp.route("/create", methods=["POST"])
@token_required
@role_required(["EMPLOYEE", "HR", "ADMIN"])
def create_approval():
    data = request.get_json()

    approval = ApprovalRequest(
        request_type=data["request_type"],
        reference_id=data.get("reference_id") or data.get("resource_id"),
        requested_by=g.user.id,
        company_id=g.user.company_id,
        status="PENDING",
        current_step=1
    )
    db.session.add(approval)
    db.session.flush()

    steps = []
    step_order = 1

    # 1. OPTIONAL MANAGER
    if data.get("require_manager"):
        steps.append(ApprovalStep(
            approval_request_id=approval.id,
            step_order=step_order,
            approver_role="MANAGER"
        ))
        step_order += 1

    # 2. HR (Mandatory)
    steps.append(ApprovalStep(
        approval_request_id=approval.id,
        step_order=step_order,
        approver_role="HR"
    ))
    step_order += 1

    # 3. OPTIONAL ADMIN
    if data.get("require_admin"):
        steps.append(ApprovalStep(
            approval_request_id=approval.id,
            step_order=step_order,
            approver_role="ADMIN"
        ))

    db.session.add_all(steps)
    db.session.commit()

    return jsonify({
        "message": "Approval workflow created",
        "approval_id": approval.id
    }), 201

@approvals_bp.route("/approve", methods=["POST"])
@token_required
@role_required(["MANAGER", "HR", "ADMIN"])
def approve_request():
    data = request.get_json()
    req_id = data["approval_request_id"]

    approval = ApprovalRequest.query.get(req_id)
    if not approval:
        return jsonify({"message": "Request not found"}), 404

    step = ApprovalStep.query.filter_by(
        approval_request_id=req_id,
        step_order=approval.current_step,
        status="PENDING"
    ).first()

    if not step or step.approver_role != g.user.role:
        return jsonify({"message": "Not authorized"}), 403

    # --- PARTIAL APPROVAL LOGIC (HR Only) ---
    if approval.request_type == "LEAVE" and g.user.role == "HR" and data.get("approved_upto"):
        try:
            leave = LeaveRequest.query.get(approval.reference_id)
            if not leave:
                return jsonify({"message": "Leave record not found"}), 404

            approved_upto = _date(data["approved_upto"])
            
            if approved_upto < leave.start_date or approved_upto > leave.end_date:
                return jsonify({"message": "Date out of range"}), 400

            # If partial approval (approved_upto < end_date)
            if approved_upto < leave.end_date:
                step.status = "APPROVED"
                step.action_at = datetime.utcnow()

                action = ApprovalAction(
                    approval_request_id=req_id,
                    action_by=g.user.id,
                    action="PARTIALLY_APPROVED",
                    remarks=f"Approved up to {data['approved_upto']}. {data.get('remarks', '')}"
                )
                db.session.add(action)

                # 1. Update Original Leave
                original_end = leave.end_date
                leave.end_date = approved_upto
                leave.total_days = (leave.end_date - leave.start_date).days + 1
                leave.status = "APPROVED"
                leave.segment_type = "APPROVED_PART"

                # 2. Create Remaining Leave
                remaining_start = _next_day(approved_upto)
                
                remaining_leave = LeaveRequest(
                    employee_id=leave.employee_id,
                    company_id=leave.company_id,
                    leave_type_id=leave.leave_type_id,
                    from_date=remaining_start,
                    to_date=original_end,
                    reason=f"Split from Leave #{leave.id}: {leave.reason}",
                    status="Pending",
                    parent_leave_id=leave.id,
                    segment_type="ESCALATED_PART"
                )
                db.session.add(remaining_leave)
                db.session.flush()

                # 3. Create New Approval (Manager -> Admin)
                new_approval = ApprovalRequest(
                    request_type="LEAVE",
                    reference_id=remaining_leave.id,
                    requested_by=approval.requested_by,
                    company_id=approval.company_id,
                    status="PENDING",
                    current_step=1
                )
                db.session.add(new_approval)
                db.session.flush()

                steps = [
                    ApprovalStep(approval_request_id=new_approval.id, step_order=1, approver_role="MANAGER"),
                    ApprovalStep(approval_request_id=new_approval.id, step_order=2, approver_role="ADMIN")
                ]
                db.session.add_all(steps)

                approval.status = "PARTIALLY_APPROVED"
                db.session.commit()

                return jsonify({
                    "message": "Partially approved. Remaining leave escalated.",
                    "approved_leave_id": leave.id,
                    "remaining_leave_id": remaining_leave.id
                })
        except ValueError:
            return jsonify({"message": "Invalid date format"}), 400
    # --- END PARTIAL APPROVAL ---

    step.status = "APPROVED"
    step.action_at = datetime.utcnow()

    action = ApprovalAction(
        approval_request_id=req_id,
        action_by=g.user.id,
        action="APPROVED",
        remarks=data.get("remarks")
    )
    db.session.add(action)

    approval.current_step += 1

    # Final approval
    next_step = ApprovalStep.query.filter_by(
        approval_request_id=req_id,
        step_order=approval.current_step
    ).first()

    if not next_step:
        approval.status = "APPROVED"
        # Update Leave status
        if approval.request_type == "LEAVE":
            leave = LeaveRequest.query.get(approval.reference_id)
            if leave: leave.status = "APPROVED"

    db.session.commit()
    return jsonify({"message": "Approved successfully"})

@approvals_bp.route("/reject", methods=["POST"])
@token_required
@role_required(["MANAGER", "HR", "ADMIN"])
def reject_request():
    data = request.get_json()
    req_id = data["approval_request_id"]

    approval = ApprovalRequest.query.get(req_id)
    if not approval:
        return jsonify({"message": "Request not found"}), 404

    approval.status = "REJECTED"
    
    if approval.request_type == "LEAVE":
        leave = LeaveRequest.query.get(approval.reference_id)
        if leave: leave.status = "REJECTED"

    action = ApprovalAction(
        approval_request_id=req_id,
        action_by=g.user.id,
        action="REJECTED",
        remarks=data.get("remarks")
    )
    db.session.add(action)
    db.session.commit()

    return jsonify({"message": "Rejected successfully"})

@approvals_bp.route("/<int:approval_id>/action", methods=["POST"])
@token_required
@role_required(["HR", "ADMIN", "MANAGER"])
def take_action(approval_id):
    data = request.get_json()
    action = data.get("action")
    
    approval = ApprovalRequest.query.get_or_404(approval_id)
    
    step = ApprovalStep.query.filter_by(
        approval_request_id=approval_id,
        step_order=approval.current_step,
        status="PENDING"
    ).first()

    if not step or step.approver_role != g.user.role:
        return jsonify({"message": "Not authorized or no pending step"}), 403

    # Mark step as completed (APPROVED even if partial reject, as the action was taken)
    step.status = "APPROVED"
    step.action_at = datetime.utcnow()

    # --- HR PARTIAL REJECT LOGIC ---
    if approval.request_type == "LEAVE" and g.user.role == "HR" and action == "PARTIAL_REJECT":
        leave = LeaveRequest.query.get(approval.reference_id)
        if not leave: return jsonify({"message": "Leave not found"}), 404

        try:
            approved_upto = _date(data["approved_upto"])
            if approved_upto < leave.from_date or approved_upto >= leave.to_date:
                return jsonify({"message": "Invalid split date"}), 400

            # A) Approve first part
            original_end = leave.to_date
            leave.to_date = approved_upto
            leave.status = "Approved"
            leave.segment_type = "APPROVED_PART"

            # B) Reject remaining part
            rejected_leave = LeaveRequest(
                employee_id=leave.employee_id,
                company_id=leave.company_id,
                leave_type_id=leave.leave_type_id,
                from_date=_next_day(approved_upto),
                to_date=original_end,
                reason=leave.reason,
                status="Rejected",
                parent_leave_id=leave.id,
                segment_type="REJECTED_PART"
            )
            db.session.add(rejected_leave)
            
            approval.status = "PARTIALLY_REJECTED"
            
            # Log action
            log = ApprovalAction(approval_request_id=approval.id, action_by=g.user.id, action="PARTIAL_REJECT", remarks=data.get("remarks"))
            db.session.add(log)
            
            db.session.commit()
            
            return jsonify({
                "message": "Partial rejection completed",
                "approved_leave_id": leave.id,
                "rejected_leave_id": rejected_leave.id
            })
        except ValueError:
            return jsonify({"message": "Invalid date format"}), 400

    return jsonify({"message": "Action not supported via this endpoint"}), 400

@approvals_bp.route("/history/<int:req_id>")
@token_required
def approval_history(req_id):
    actions = ApprovalAction.query.filter_by(
        approval_request_id=req_id
    ).all()

    return jsonify([
        {
            "action": a.action,
            "by": a.action_by,
            "remarks": a.remarks,
            "at": a.action_at
        } for a in actions
    ])

@approvals_bp.route("/pending", methods=["GET"])
@token_required
def pending_approvals():
    # Find steps where role matches user role and status is PENDING
    pending_steps = ApprovalStep.query.filter_by(
        approver_role=g.user.role,
        status="PENDING"
    ).all()
    
    results = []
    for step in pending_steps:
        approval = ApprovalRequest.query.get(step.approval_request_id)
        # Check if this step is the current active step and company matches
        if approval and approval.status == "PENDING" and approval.current_step == step.step_order and approval.company_id == g.user.company_id:
            results.append({
                "approval_id": approval.id,
                "request_type": approval.request_type,
                "reference_id": approval.reference_id,
                "requested_by": approval.requested_by,
                "created_at": approval.created_at
            })
    
    return jsonify(results)