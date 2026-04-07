# routes/loan_routes.py
from flask import Blueprint, jsonify, request, g
from models import db
from models.loan import Loan
from models.employee import Employee
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import calendar

loan_bp = Blueprint('loan', __name__)

def has_loan_management_permission():
    """Helper to check if user can see ALL loans."""
    # This is a bit of a workaround since permission_required is a decorator
    # We can check g.user.permissions if it's loaded, or just check role
    return g.user.role in ['ADMIN', 'SUPER_ADMIN', 'HR']

@loan_bp.route('/dashboard', methods=['GET'])
@token_required
def get_loan_dashboard():
    """
    Stats and Charts. Scoped to Employee if not Admin/HR.
    """
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)
    
    # Context Selection
    is_admin = has_loan_management_permission()
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    
    # Filter Base
    base_q = Loan.query.filter(Loan.company_id == company_id)
    if not is_admin:
        if not emp_id:
            return jsonify({"success": False, "message": "Employee profile required"}), 400
        base_q = base_q.filter(Loan.employee_id == emp_id)

    # 1. Total Disbursed
    total_disbursed = db.session.query(func.sum(Loan.amount)).filter(
        Loan.company_id == company_id,
        Loan.status.in_(['APPROVED', 'ACTIVE', 'PAID'])
    )
    if not is_admin:
        total_disbursed = total_disbursed.filter(Loan.employee_id == emp_id)
    total_disbursed = total_disbursed.scalar() or 0.0

    # 2. Active Loans
    active_loans_count = base_q.filter(Loan.status == 'ACTIVE').count()

    # 3. Avg. Interest Rate
    avg_interest = db.session.query(func.avg(Loan.interest_rate)).filter(
        Loan.company_id == company_id,
        Loan.status == 'ACTIVE'
    )
    if not is_admin:
        avg_interest = avg_interest.filter(Loan.employee_id == emp_id)
    avg_interest = avg_interest.scalar() or 0.0

    # 4. Loan Type Distribution
    type_dist = db.session.query(Loan.loan_type, func.count(Loan.id)).filter(
        Loan.company_id == company_id
    )
    if not is_admin:
        type_dist = type_dist.filter(Loan.employee_id == emp_id)
    type_dist = type_dist.group_by(Loan.loan_type).all()
    
    type_distribution = [{"type": t[0], "total": t[1]} for t in type_dist]

    # 5. Monthly Disbursement Trend
    trend = []
    now = datetime.utcnow()
    for i in range(4, -1, -1):
        target_date = now - timedelta(days=i*30)
        month, year = target_date.month, target_date.year
        month_name = calendar.month_name[month][:3]
        
        start_of_month = datetime(year, month, 1)
        if month == 12: end_of_month = datetime(year + 1, 1, 1)
        else: end_of_month = datetime(year, month + 1, 1)
            
        monthly_sum_q = db.session.query(func.sum(Loan.amount)).filter(
             Loan.company_id == company_id,
             Loan.disbursement_date >= start_of_month.date(),
             Loan.disbursement_date < end_of_month.date(),
             Loan.status.in_(['APPROVED', 'ACTIVE', 'PAID'])
        )
        if not is_admin:
            monthly_sum_q = monthly_sum_q.filter(Loan.employee_id == emp_id)
            
        monthly_sum = monthly_sum_q.scalar() or 0.0
        trend.append({"month": month_name, "amount": monthly_sum})

    return jsonify({
        "success": True,
        "data": {
            "stats": {
                "total_disbursed": total_disbursed,
                "active_loans": active_loans_count,
                "avg_interest_rate": round(avg_interest, 1)
            },
            "charts": {
                "type_distribution": type_distribution,
                "disbursement_trend": trend
            }
        }
    })

@loan_bp.route('/requests', methods=['GET'])
@token_required
def get_loan_requests():
    """
    List of loan requests. Filtered by Self if not Admin.
    """
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)

    is_admin = has_loan_management_permission()
    
    q = Loan.query.filter_by(company_id=company_id)
    if not is_admin:
        emp_id = g.user.employee_profile.id if g.user.employee_profile else None
        if not emp_id: return jsonify({"success": True, "data": []}), 200
        q = q.filter_by(employee_id=emp_id)

    loans = q.order_by(Loan.created_at.desc()).limit(20).all()
    
    return jsonify({
        "success": True,
        "data": [loan.to_dict() for loan in loans]
    })

@loan_bp.route('/apply', methods=['POST'])
@token_required
def apply_loan():
    """
    Employee applying for a loan.
    """
    data = request.get_json()
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile required to apply for a loan"}), 400
        
    # Calculate EMI
    amount = float(data.get('amount', 0))
    tenure = int(data.get('tenure_months', 12))
    interest = float(data.get('interest_rate', 8.5))
    
    if amount <= 0 or tenure <= 0:
        return jsonify({"success": False, "message": "Amount and Tenure must be greater than zero"}), 400
        
    # Total interest = Amount * Interest% * (Tenure/12)
    total_interest = amount * (interest / 100) * (tenure / 12)
    total_payable = amount + total_interest
    emi = total_payable / tenure

    new_loan = Loan(
        company_id=g.user.company_id,
        employee_id=emp_id,
        loan_type=data.get('loan_type', 'Personal'),
        amount=amount,
        interest_rate=interest,
        tenure_months=tenure,
        emi=round(emi, 2),
        reason=data.get('reason'),
        status='PENDING'
    )
    
    db.session.add(new_loan)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Loan application submitted successfully", 
        "loan": new_loan.to_dict()
    }), 201

@loan_bp.route('/<int:loan_id>/action', methods=['PATCH'])
@token_required
@permission_required(Permissions.LOAN_MANAGEMENT)
def loan_action(loan_id):
    """
    Admin Approve/Reject action.
    """
    loan = Loan.query.get(loan_id)
    if not loan or loan.company_id != g.user.company_id:
        return jsonify({"success": False, "message": "Loan not found"}), 404

    data = request.get_json()
    action = data.get('action') # APPROVE or REJECT
    
    if action == 'APPROVE':
        loan.status = 'ACTIVE'
        loan.disbursement_date = datetime.utcnow().date()
    elif action == 'REJECT':
        loan.status = 'REJECTED'
    
    db.session.commit()
    return jsonify({"success": True, "message": f"Loan {action}ed successfully"})
