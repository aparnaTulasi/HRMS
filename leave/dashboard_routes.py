from flask import request, jsonify, g
from datetime import datetime
from sqlalchemy import func
from . import leave_bp
from .models import LeaveType, LeavePolicy, LeavePolicyMapping, LeaveRequest, LeaveBalance, LeaveLedger
from models import db
from models.employee import Employee
from utils.decorators import token_required, role_required, permission_required
from constants.permissions_registry import Permissions

# ==============================================================================
# Dashboard & Management Control APIs
# ==============================================================================

@leave_bp.route('/dashboard/summary', methods=['GET'])
@token_required
@permission_required(Permissions.LEAVE_VIEW)
def get_leave_dashboard_summary():
    company_id = g.user.company_id
    
    # 1. Summary Counts
    pending = LeaveRequest.query.filter_by(company_id=company_id, status='Pending').count()
    approved = LeaveRequest.query.filter_by(company_id=company_id, status='Approved').count()
    rejected = LeaveRequest.query.filter_by(company_id=company_id, status='Rejected').count()
    
    # Total balance aggregation across all employees
    total_balance = db.session.query(func.sum(LeaveBalance.balance)).filter(
        LeaveBalance.employee_id.in_(
            db.session.query(Employee.id).filter_by(company_id=company_id)
        )
    ).scalar() or 0
    
    # 2. Entitlement Progress Bars (Averaged/Aggregated for the company)
    entitlements = []
    target_codes = ['CL', 'SL', 'EL', 'PL']
    colors = {'CL': 'blue', 'SL': 'green', 'EL': 'orange', 'PL': 'orange'}
    
    leave_types = LeaveType.query.filter(LeaveType.company_id == company_id, LeaveType.code.in_(target_codes)).all()
    
    distribution = []
    for lt in leave_types:
        mapping = LeavePolicyMapping.query.filter_by(company_id=company_id, leave_type_id=lt.id).first()
        total_alloc = mapping.annual_allocation if mapping else 0
        
        current_year = datetime.utcnow().year
        used = db.session.query(func.sum(LeaveLedger.units)).filter(
            LeaveLedger.company_id == company_id,
            LeaveLedger.leave_type_id == lt.id,
            LeaveLedger.txn_type == 'DEBIT',
            LeaveLedger.created_at >= datetime(current_year, 1, 1)
        ).scalar() or 0
        
        entitlements.append({
            'type': lt.name,
            'code': lt.code,
            'used': round(float(used), 1),
            'total': round(float(total_alloc), 1),
            'color': colors.get(lt.code, 'gray')
        })
        
        distribution.append({
            'name': lt.code,
            'value': round(float(used), 1)
        })

    total_used = sum(d['value'] for d in distribution)
    distribution.append({
        'name': 'Remaining',
        'value': round(max(0, float(total_balance) - total_used), 1)
    })

    return jsonify({
        'counts': {
            'total_balance': round(float(total_balance), 1),
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        },
        'entitlements': entitlements,
        'distribution': distribution
    }), 200

@leave_bp.route('/dashboard/trends', methods=['GET'])
@token_required
@permission_required(Permissions.LEAVE_VIEW)
def get_leave_dashboard_trends():
    company_id = g.user.company_id
    current_year = datetime.utcnow().year
    trends = []
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for m in range(1, 13):
        start_date = datetime(current_year, m, 1)
        if m == 12:
            end_date = datetime(current_year + 1, 1, 1)
        else:
            end_date = datetime(current_year, m + 1, 1)
            
        count = db.session.query(func.count(LeaveRequest.id)).filter(
            LeaveRequest.company_id == company_id,
            LeaveRequest.status == 'Approved',
            LeaveRequest.from_date >= start_date.date(),
            LeaveRequest.from_date < end_date.date()
        ).scalar() or 0
        
        trends.append({
            'month': month_names[m-1],
            'leaves': count
        })
        
    return jsonify(trends), 200

@leave_bp.route('/dashboard/recent', methods=['GET'])
@token_required
@permission_required(Permissions.LEAVE_VIEW)
def get_leave_dashboard_recent():
    company_id = g.user.company_id
    recent_requests = db.session.query(LeaveRequest, Employee, LeaveType).filter(
        LeaveRequest.company_id == company_id,
        LeaveRequest.employee_id == Employee.id,
        LeaveRequest.leave_type_id == LeaveType.id
    ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
        
    results = []
    for req, emp, lt in recent_requests:
        results.append({
            'id': req.id,
            'employee': emp.full_name,
            'type': lt.name,
            'period': f"{req.from_date.strftime('%b %d')} - {req.to_date.strftime('%b %d')}",
            'days': f"{(req.to_date - req.from_date).days + 1}d",
            'status': req.status
        })
        
    return jsonify(results), 200

@leave_bp.route('/bulk-action', methods=['POST'])
@token_required
@permission_required(Permissions.LEAVE_APPROVE)
def leave_bulk_action():
    data = request.get_json()
    ids = data.get('ids', [])
    action = data.get('action', '').upper()
    
    if not ids or action not in ['APPROVE', 'REJECT']:
        return jsonify({'message': 'Invalid request components'}), 400
        
    status = 'Approved' if action == 'APPROVE' else 'Rejected'
    approver_emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    updated_count = 0
    for req_id in ids:
        req = LeaveRequest.query.filter_by(id=req_id, company_id=g.user.company_id, status='Pending').first()
        if req:
            req.status = status
            req.approved_by = approver_emp.id if approver_emp else None
            updated_count += 1
            
    db.session.commit()
    return jsonify({'message': f'Bulk {action.lower()} processed', 'count': updated_count}), 200

# ==============================================================================
# My Leaves (Employee Perspective) Dashboard APIs
# ==============================================================================

@leave_bp.route('/my-dashboard/summary', methods=['GET'])
@token_required
def get_my_leave_dashboard_summary():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404
    
    company_id = emp.company_id
    
    # 1. Summary Counts
    pending = LeaveRequest.query.filter_by(employee_id=emp.id, status='Pending').count()
    approved = LeaveRequest.query.filter_by(employee_id=emp.id, status='Approved').count()
    rejected = LeaveRequest.query.filter_by(employee_id=emp.id, status='Rejected').count()
    
    total_balance = db.session.query(func.sum(LeaveBalance.balance)).filter_by(employee_id=emp.id).scalar() or 0
    
    # 2. Balance Distribution (Sick, Casual, Privilege, Used)
    # The UI shows "Sick", "Casual", "Privilege", "Used". 
    # Let's map these to common codes: SL, CL, EL/PL, and sum of debits for 'Used'.
    
    target_codes = ['SL', 'CL', 'EL', 'PL']
    balances = db.session.query(LeaveBalance, LeaveType).join(LeaveType).filter(
        LeaveBalance.employee_id == emp.id,
        LeaveType.code.in_(target_codes)
    ).all()
    
    # Mapping for UI-friendly names
    ui_labels = {
        'SL': 'Sick',
        'CL': 'Casual',
        'EL': 'Privilege',
        'PL': 'Privilege'
    }
    
    distribution = []
    found_codes = set()
    for bal, lt in balances:
        name = ui_labels.get(lt.code, lt.name.split('(')[0].strip())
        distribution.append({
            'name': name,
            'code': lt.code,
            'value': round(float(bal.balance), 1)
        })
        found_codes.add(lt.code)
    
    # Ensure all target sections exist even if 0
    for code, label in ui_labels.items():
        if code not in found_codes and code != 'PL': # PL/EL are merged
            if code == 'EL' and 'PL' in found_codes: continue
            distribution.append({
                'name': label,
                'code': code,
                'value': 0.0
            })
    
    # Calculate "Used"
    current_year = datetime.utcnow().year
    used = db.session.query(func.sum(LeaveLedger.units)).filter(
        LeaveLedger.employee_id == emp.id,
        LeaveLedger.txn_type == 'DEBIT',
        LeaveLedger.created_at >= datetime(current_year, 1, 1)
    ).scalar() or 0
    
    distribution.append({
        'name': 'Used',
        'code': 'USED',
        'value': round(float(used), 1)
    })

    return jsonify({
        'counts': {
            'total_balance': round(float(total_balance), 1),
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        },
        'distribution': distribution
    }), 200

@leave_bp.route('/my-dashboard/trends', methods=['GET'])
@token_required
def get_my_leave_dashboard_trends():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404
        
    current_year = datetime.utcnow().year
    trends = []
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for m in range(1, 13):
        start_date = datetime(current_year, m, 1)
        if m == 12:
            end_date = datetime(current_year + 1, 1, 1)
        else:
            end_date = datetime(current_year, m + 1, 1)
            
        count = db.session.query(func.count(LeaveRequest.id)).filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status == 'Approved',
            LeaveRequest.from_date >= start_date.date(),
            LeaveRequest.from_date < end_date.date()
        ).scalar() or 0
        
        trends.append({
            'month': month_names[m-1],
            'leaves': count
        })
        
    return jsonify(trends), 200

@leave_bp.route('/my-dashboard/recent', methods=['GET'])
@token_required
def get_my_leave_dashboard_recent():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404
        
    recent_requests = db.session.query(LeaveRequest, LeaveType).join(LeaveType).filter(
        LeaveRequest.employee_id == emp.id
    ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
        
    results = []
    for req, lt in recent_requests:
        results.append({
            'id': req.id,
            'type': lt.name,
            'period': f"{req.from_date.strftime('%b %d')} - {req.to_date.strftime('%b %d')}",
            'days': f"{(req.to_date - req.from_date).days + 1}d", # Simplistic, could use units if available
            'status': req.status
        })
        
    return jsonify(results), 200
