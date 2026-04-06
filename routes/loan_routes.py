from flask import Blueprint, jsonify, request, g
from models import db
from models.loan import Loan
from models.employee import Employee
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from sqlalchemy import func
from datetime import datetime, timedelta
import calendar

loan_bp = Blueprint('loan', __name__)

@loan_bp.route('/dashboard', methods=['GET'])
@token_required
@permission_required("LOAN_VIEW")
def get_loan_dashboard():
    # Only Admin, HR, and Super Admin can access the dashboard stats - handled by permission

    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 3, type=int)
    
    # 1. Total Disbursed
    total_disbursed = db.session.query(func.sum(Loan.amount)).filter(
        Loan.company_id == company_id,
        Loan.status.in_(['APPROVED', 'ACTIVE', 'PAID'])
    ).scalar() or 0.0

    # 2. Active Loans
    active_loans_count = Loan.query.filter_by(company_id=company_id, status='ACTIVE').count()

    # 3. Avg. Interest Rate
    avg_interest = db.session.query(func.avg(Loan.interest_rate)).filter(
        Loan.company_id == company_id,
        Loan.status == 'ACTIVE'
    ).scalar() or 0.0

    # 4. Loan Type Distribution (Donut Chart)
    type_dist = db.session.query(Loan.loan_type, func.count(Loan.id)).filter(
        Loan.company_id == company_id
    ).group_by(Loan.loan_type).all()
    
    type_distribution = [{"type": t[0], "total": t[1]} for t in type_dist]

    # 5. Monthly Disbursement Trend (Bar Chart)
    trend = []
    now = datetime.utcnow()
    for i in range(4, -1, -1):
        target_date = now - timedelta(days=i*30)
        month = target_date.month
        year = target_date.year
        month_name = calendar.month_name[month][:3]
        
        # SQLite compatible month/year extraction using strftime
        monthly_sum = db.session.query(func.sum(Loan.amount)).filter(
             Loan.company_id == company_id,
             func.strftime('%m', Loan.disbursement_date) == f"{month:02d}",
             func.strftime('%Y', Loan.disbursement_date) == str(year),
             Loan.status.in_(['APPROVED', 'ACTIVE', 'PAID'])
        ).scalar() or 0.0
        
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
@permission_required("LOAN_VIEW")
def get_loan_requests():
    # Role check now handled by permission decorator

    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 3, type=int)

    loans = Loan.query.filter_by(company_id=company_id).order_by(Loan.created_at.desc()).limit(10).all()
    
    return jsonify({
        "success": True,
        "data": [loan.to_dict() for loan in loans]
    })

@loan_bp.route('/apply', methods=['POST'])
@token_required
def apply_loan():
    data = request.get_json()
    
    # Calculate EMI (Simple logic for now)
    amount = float(data.get('amount', 0))
    tenure = int(data.get('tenure_months', 12))
    interest = float(data.get('interest_rate', 8.5))
    
    # Total interest = Amount * Interest% * (Tenure/12)
    total_interest = amount * (interest / 100) * (tenure / 12)
    total_payable = amount + total_interest
    emi = total_payable / tenure

    new_loan = Loan(
        company_id=g.user.company_id,
        employee_id=g.user.employee_profile.id,
        loan_type=data.get('loan_type'),
        amount=amount,
        interest_rate=interest,
        tenure_months=tenure,
        emi=round(emi, 2),
        reason=data.get('reason'),
        status='PENDING'
    )
    
    db.session.add(new_loan)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Loan application submitted successfully", "loan": new_loan.to_dict()})

@loan_bp.route('/<int:loan_id>/action', methods=['PATCH'])
@token_required
@permission_required(Permissions.LOAN_MANAGEMENT)
def loan_action(loan_id):
    # Role check now handled by permission decorator

    loan = Loan.query.get(loan_id)
    if not loan or loan.company_id != g.user.company_id:
        return jsonify({"success": False, "message": "Loan not found"}), 404

    data = request.get_json()
    action = data.get('action') # APPROVE or REJECT
    
    if action == 'APPROVE':
        loan.status = 'APPROVED'
        loan.disbursement_date = datetime.utcnow().date()
        # In a real system, you might set it to ACTIVE once disbursed
        loan.status = 'ACTIVE'
    elif action == 'REJECT':
        loan.status = 'REJECTED'
    
    db.session.commit()
    return jsonify({"success": True, "message": f"Loan {action}ed successfully"})
