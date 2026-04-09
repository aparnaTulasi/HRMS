# routes/delegation_routes.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime, date
from models import db
from models.delegation import Delegation
from models.employee import Employee
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from sqlalchemy import desc, or_, func
from utils.date_utils import parse_date

delegation_bp = Blueprint('delegation', __name__)

@delegation_bp.route('/stats', methods=['GET'])
@token_required
def get_delegation_stats():
    """
    Summary counts for delegation dashboard cards.
    """
    cid = g.user.company_id
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile required"}), 400
        
    today = date.today()
    
    # Role Scoping
    is_admin = g.user.role in ['ADMIN', 'SUPER_ADMIN', 'HR']
    
    # Active
    active_q = Delegation.query.filter(
        Delegation.company_id == cid,
        Delegation.status == 'ACTIVE',
        Delegation.start_date <= today,
        Delegation.end_date >= today
    )
    
    # Expired
    expired_q = Delegation.query.filter(
        Delegation.company_id == cid,
        or_(Delegation.status == 'EXPIRED', Delegation.end_date < today)
    )
    
    # Total
    total_q = Delegation.query.filter_by(company_id=cid)
    
    if not is_admin:
        active_q = active_q.filter(Delegation.delegated_by_id == emp_id)
        expired_q = expired_q.filter(Delegation.delegated_by_id == emp_id)
        total_q = total_q.filter(Delegation.delegated_by_id == emp_id)
        
    active_count = active_q.count()
    expired_count = expired_q.count()
    total_logs = total_q.count()
    
    return jsonify({
        "success": True,
        "data": {
            "active_delegations": active_count,
            "expired_count": expired_count,
            "total_logs": total_logs
        }
    })

@delegation_bp.route('/list', methods=['GET'])
@token_required
def list_delegations():
    """
    Fetches history of delegations.
    """
    cid = g.user.company_id
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    if not emp_id:
        return jsonify({"success": True, "data": []}), 200
        
    search = request.args.get('search', '').strip().lower()
    
    # Role Scoping
    is_admin = g.user.role in ['ADMIN', 'SUPER_ADMIN', 'HR']
    
    q = Delegation.query.filter(Delegation.company_id == cid)
    if not is_admin:
        # Managers/Employees see delegations delegated BY them OR TO them
        q = q.filter(or_(Delegation.delegated_by_id == emp_id, Delegation.delegated_to_id == emp_id))
    
    if search:
        # Search by notes or module or names
        q = q.join(Employee, or_(Employee.id == Delegation.delegated_by_id, Employee.id == Delegation.delegated_to_id))
        q = q.filter(or_(
            func.lower(Delegation.module).like(f"%{search}%"),
            func.lower(Delegation.notes).like(f"%{search}%"),
            func.lower(Employee.full_name).like(f"%{search}%")
        ))

    rows = q.order_by(desc(Delegation.created_at)).all()
    
    output = []
    today = date.today()
    for d in rows:
        # Dynamic status check for display
        display_status = d.status
        if d.status == 'ACTIVE' and d.end_date < today:
            display_status = 'EXPIRED'
            
        output.append({
            "id": d.id,
            "delegated_by": d.delegator.full_name if d.delegator else "N/A",
            "delegated_to": d.delegatee.full_name if d.delegatee else "N/A",
            "module": d.module,
            "validity": f"{d.start_date.strftime('%Y-%m-%d')} to {d.end_date.strftime('%Y-%m-%d')}",
            "status": display_status,
            "notes": d.notes
        })
        
    return jsonify({"success": True, "data": output}), 200

@delegation_bp.route('/create', methods=['POST'])
@token_required
def create_delegation():
    """
    Creates a new delegation.
    """
    data = request.get_json()
    delegated_to_id = data.get('delegated_to_id')
    module = data.get('module', 'All')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    notes = data.get('notes')
    
    if not delegated_to_id or not start_date_str or not end_date_str:
        return jsonify({"success": False, "message": "Receiver, Start Date, and End Date are required"}), 400
        
    try:
        s_date = parse_date(start_date_str)
        e_date = parse_date(end_date_str)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
        
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile required"}), 400
        
    if int(delegated_to_id) == emp_id:
        return jsonify({"success": False, "message": "Cannot delegate authority to yourself"}), 400

    new_del = Delegation(
        company_id=g.user.company_id,
        delegated_by_id=emp_id,
        delegated_to_id=delegated_to_id,
        module=module,
        start_date=s_date,
        end_date=e_date,
        notes=notes,
        status='ACTIVE'
    )
    db.session.add(new_del)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Authority delegated successfully", "delegation_id": new_del.id}), 201

@delegation_bp.route('/cancel/<int:id>', methods=['POST'])
@token_required
def cancel_delegation(id):
    """
    Cancels an active delegation.
    """
    d = Delegation.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    
    if d.status != 'ACTIVE':
        return jsonify({"success": False, "message": "Only active delegations can be cancelled"}), 400
        
    d.status = 'CANCELLED'
    db.session.commit()
    
    return jsonify({"success": True, "message": "Delegation cancelled successfully"}), 200
