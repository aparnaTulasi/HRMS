# routes/visitor_routes.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime, date
from models import db
from models.visitor import VisitorRequest
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from sqlalchemy import desc, func, or_
from utils.date_utils import parse_date

visitor_bp = Blueprint('visitor', __name__)

@visitor_bp.route('/request', methods=['POST'])
@token_required
@permission_required(Permissions.VISITOR_CREATE)
def create_visitor_request():
    """
    Creates a new visitor entry request.
    """
    data = request.get_json()
    
    visitor_name = data.get('visitor_name')
    organization = data.get('organization')
    phone_number = data.get('phone_number')
    visit_date_str = data.get('visit_date')
    preferred_time = data.get('preferred_time')
    meeting_with_employee_id = data.get('meeting_with_employee_id')
    purpose = data.get('purpose')
    
    if not visitor_name or not visit_date_str or not meeting_with_employee_id:
        return jsonify({"success": False, "message": "Visitor Name, Date, and Host are required"}), 400
    
    try:
        v_date = parse_date(visit_date_str)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    new_request = VisitorRequest(
        company_id=g.user.company_id,
        visitor_name=visitor_name,
        organization=organization,
        phone_number=phone_number,
        visit_date=v_date,
        preferred_time=preferred_time,
        meeting_with_employee_id=meeting_with_employee_id,
        purpose=purpose,
        status='PENDING',
        created_by=g.user.id
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Visitor request submitted successfully",
        "request_id": new_request.id
    }), 201

@visitor_bp.route('/list', methods=['GET'])
@token_required
@permission_required(Permissions.VISITOR_VIEW)
def list_visitor_requests():
    """
    Fetches visitor requests based on filters (tab, search, date).
    Tabs mapped to status:
    - 'request': PENDING, APPROVED, REJECTED
    - 'approvals': PENDING
    - 'log': CHECKED_IN, CHECKED_OUT
    """
    tab = request.args.get('tab', 'request') # request, approvals, log
    search = request.args.get('search', '').strip().lower()
    status_filter = request.args.get('status')
    
    q = VisitorRequest.query.filter_by(company_id=g.user.company_id)
    
    # Tab Logic
    if tab == 'approvals':
        q = q.filter_by(status='PENDING')
    elif tab == 'log':
        q = q.filter(VisitorRequest.status.in_(['CHECKED_IN', 'CHECKED_OUT']))
    
    # Specific Status Filter
    if status_filter:
        q = q.filter_by(status=status_filter.upper())
        
    # Search logic (Visitor Name, Host Name, Organization, Purpose)
    if search:
        q = q.join(Employee, Employee.id == VisitorRequest.meeting_with_employee_id)
        q = q.filter(or_(
            func.lower(VisitorRequest.visitor_name).like(f"%{search}%"),
            func.lower(VisitorRequest.organization).like(f"%{search}%"),
            func.lower(VisitorRequest.purpose).like(f"%{search}%"),
            func.lower(Employee.full_name).like(f"%{search}%")
        ))

    rows = q.order_by(desc(VisitorRequest.visit_date), desc(VisitorRequest.created_at)).all()
    
    output = []
    for r in rows:
        output.append({
            "id": r.id,
            "visitor_name": r.visitor_name,
            "organization": r.organization,
            "phone_number": r.phone_number,
            "purpose": r.purpose,
            "host_name": r.employee.full_name if r.employee else "N/A",
            "host_id": r.meeting_with_employee_id,
            "visit_date": r.visit_date.strftime("%Y-%m-%d"),
            "preferred_time": r.preferred_time,
            "status": r.status,
            "check_in_time": r.check_in_time.strftime("%I:%M %p") if r.check_in_time else None,
            "check_out_time": r.check_out_time.strftime("%I:%M %p") if r.check_out_time else None
        })
        
    return jsonify({"success": True, "data": output}), 200

@visitor_bp.route('/action/<int:request_id>', methods=['POST'])
@token_required
def visitor_action(request_id):
    """
    Manages Approve, Reject, Check-In, Check-Out.
    """
    data = request.get_json()
    action = data.get('action') # APPROVE, REJECT, CHECK_IN, CHECK_OUT
    
    v_req = VisitorRequest.query.filter_by(id=request_id, company_id=g.user.company_id).first()
    if not v_req:
        return jsonify({"success": False, "message": "Request not found"}), 404
        
    if action == 'APPROVE':
        v_req.status = 'APPROVED'
        v_req.action_by = g.user.id
        v_req.action_at = datetime.utcnow()
    elif action == 'REJECT':
        v_req.status = 'REJECTED'
        v_req.action_by = g.user.id
        v_req.action_at = datetime.utcnow()
    elif action == 'CHECK_IN':
        v_req.status = 'CHECKED_IN'
        v_req.check_in_time = datetime.now()
    elif action == 'CHECK_OUT':
        v_req.status = 'CHECKED_OUT'
        v_req.check_out_time = datetime.now()
    else:
        return jsonify({"success": False, "message": "Invalid action"}), 400
        
    db.session.commit()
    return jsonify({"success": True, "message": f"Visitor {action.lower()} successfully", "status": v_req.status}), 200

@visitor_bp.route('/stats', methods=['GET'])
@token_required
def get_visitor_stats():
    """
    Daily summary for visitor dashboard.
    """
    today = date.today()
    cid = g.user.company_id
    
    expected = VisitorRequest.query.filter(
        VisitorRequest.company_id == cid,
        VisitorRequest.visit_date == today,
        VisitorRequest.status.in_(['PENDING', 'APPROVED'])
    ).count()
    
    inside = VisitorRequest.query.filter(
        VisitorRequest.company_id == cid,
        VisitorRequest.status == 'CHECKED_IN'
    ).count()
    
    completed = VisitorRequest.query.filter(
        VisitorRequest.company_id == cid,
        VisitorRequest.visit_date == today,
        VisitorRequest.status == 'CHECKED_OUT'
    ).count()
    
    # Alerts Example (overstaying > 4 hours)
    # real calculation would be: check_in_time < datetime.now() - 4 hours
    
    return jsonify({
        "success": True,
        "data": {
            "total_expected": expected,
            "inside_premise": inside,
            "completed": completed
        }
    })

@visitor_bp.route('/staff-list', methods=['GET'])
@token_required
def get_staff_list():
    """
    Dropdown for host selection.
    """
    staff = Employee.query.filter_by(company_id=g.user.company_id, status='ACTIVE').order_by(Employee.full_name).all()
    output = [{"id": s.id, "name": s.full_name, "designation": s.designation} for s in staff]
    return jsonify({"success": True, "data": output}), 200

@visitor_bp.route('/print/<int:request_id>', methods=['GET'])
@token_required
def get_print_pass(request_id):
    """
    Exports visitor pass data for printing and downloading.
    """
    v = VisitorRequest.query.filter_by(id=request_id, company_id=g.user.company_id).first()
    if not v:
        return jsonify({"success": False, "message": "Request not found"}), 404
        
    pass_data = {
        "pass_no": f"VST-{v.id:04d}",
        "visitor_name": v.visitor_name,
        "organization": v.organization,
        "visitor_phone": v.phone_number,
        "host_name": v.employee.full_name if v.employee else "N/A",
        "visit_date": v.visit_date.strftime("%B %d, %Y"),
        "visit_time": v.preferred_time,
        "purpose": v.purpose,
        "checked_in_at": v.check_in_time.strftime("%I:%M %p") if v.check_in_time else "---",
        "status": v.status
    }
    
    return jsonify({"success": True, "data": pass_data}), 200
