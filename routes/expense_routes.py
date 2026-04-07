# routes/expense_routes.py
from flask import Blueprint, request, jsonify, g
from models import db
from models.expense import ExpenseClaim
from models.employee import Employee
from utils.decorators import token_required, role_required, permission_required
from constants.permissions_registry import Permissions
from utils.audit_logger import log_action
from datetime import datetime, date, timedelta
import sqlalchemy as sa
from sqlalchemy import or_
import calendar
from utils.date_utils import parse_date

expense_bp = Blueprint("expenses", __name__)

def is_management():
    """Admin/HR check for visibility."""
    return g.user.role in ['ADMIN', 'SUPER_ADMIN', 'HR', 'MANAGER']

@expense_bp.route("/stats", methods=['GET'])
@token_required
def expense_stats():
    cid = g.user.company_id
    is_mgr = is_management()
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    
    # 1. Total Expenses (YTD)
    current_year = date.today().year
    ytd_q = db.session.query(sa.func.sum(ExpenseClaim.amount)).filter(
        ExpenseClaim.company_id == cid,
        ExpenseClaim.status == "APPROVED",
        ExpenseClaim.year == current_year
    )
    if not is_mgr:
        ytd_q = ytd_q.filter(ExpenseClaim.employee_id == emp_id)
    total_ytd = ytd_q.scalar() or 0
    
    # 2. Pending Claims
    pending_q = ExpenseClaim.query.filter_by(company_id=cid, status="PENDING")
    if not is_mgr:
        pending_q = pending_q.filter_by(employee_id=emp_id)
    pending_count = pending_q.count()
    
    # 3. Approved Trips
    trips_q = ExpenseClaim.query.filter(
        ExpenseClaim.company_id == cid,
        ExpenseClaim.status == "APPROVED",
        ExpenseClaim.category.in_(["Flight", "Hotel", "Taxi"])
    )
    if not is_mgr:
        trips_q = trips_q.filter(ExpenseClaim.employee_id == emp_id)
    
    return jsonify({
        "success": True,
        "data": {
            "total_expenses_ytd": total_ytd,
            "pending_claims": pending_count,
            "approved_trips": trips_q.count(),
            "currency": "$"
        }
    })

@expense_bp.route("/trends", methods=['GET'])
@token_required
def expense_trends():
    cid = g.user.company_id
    is_mgr = is_management()
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    
    trend = []
    now = date.today()
    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i*30)
        m, y = target_date.month, target_date.year
        month_name = calendar.month_name[m][:3]
        
        q = db.session.query(sa.func.sum(ExpenseClaim.amount)).filter(
            ExpenseClaim.company_id == cid,
            ExpenseClaim.status == "APPROVED",
            ExpenseClaim.month == m,
            ExpenseClaim.year == y
        )
        if not is_mgr:
            q = q.filter(ExpenseClaim.employee_id == emp_id)
            
        monthly_sum = q.scalar() or 0
        trend.append({"month": month_name, "amount": monthly_sum})
        
    return jsonify({"success": True, "data": trend})

@expense_bp.route("/claims", methods=['GET'])
@token_required
def expense_claims_list():
    cid = g.user.company_id
    is_mgr = is_management()
    
    q = ExpenseClaim.query.filter_by(company_id=cid)
    if not is_mgr:
        emp_id = g.user.employee_profile.id if g.user.employee_profile else None
        if not emp_id: return jsonify({"success": True, "data": []}), 200
        q = q.filter_by(employee_id=emp_id)
        
    items = q.order_by(ExpenseClaim.created_at.desc()).limit(30).all()
    return jsonify({"success": True, "data": [x.to_dict() for x in items]})

@expense_bp.route("/claims", methods=['POST'])
@token_required
def expense_claim_submit():
    payload = request.get_json()
    e_date_str = payload.get("expense_date")
    if not e_date_str:
        return jsonify({"success": False, "message": "Date is required"}), 400
        
    try:
        e_date = parse_date(e_date_str)
    except ValueError as ex:
        return jsonify({"success": False, "message": str(ex)}), 400
        
    now = datetime.now()
    emp_profile = g.user.employee_profile
    if not emp_profile:
        return jsonify({"success": False, "message": "Employee profile required"}), 400
    
    claim = ExpenseClaim(
        company_id=g.user.company_id,
        employee_id=emp_profile.id,
        project_purpose=payload.get("project_purpose", "Business Expense"),
        category=payload.get("category", "Others"),
        amount=float(payload.get("amount", 0)),
        currency=payload.get("currency", "$"),
        expense_date=e_date,
        description=payload.get("description"),
        status="PENDING",
        
        # User specified data requirements: Day, Time, Year, Month
        year=e_date.year,
        month=e_date.month,
        day=e_date.day,
        time=now.strftime("%H:%M:%S"),
        added_by_name=g.user.name # Using model property for full name
    )
    db.session.add(claim)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Expense claim submitted successfully",
        "data": {"id": claim.id}
    }), 201

@expense_bp.route("/claims/<int:cid>/action", methods=['PATCH'])
@token_required
@permission_required(Permissions.EXPENSE_APPROVE)
def expense_claim_action(cid):
    payload = request.get_json()
    action = payload.get("action") # APPROVE, REJECT
    
    claim = ExpenseClaim.query.filter_by(id=cid, company_id=g.user.company_id).first_or_404()
        
    if action == "APPROVE":
        claim.status = "APPROVED"
        claim.approved_by = g.user.employee_profile.id if g.user.employee_profile else None
        claim.approved_at = datetime.utcnow()
    elif action == "REJECT":
        claim.status = "REJECTED"
        claim.rejection_reason = payload.get("reason")
        
    db.session.commit()
    
    return jsonify({"success": True, "message": f"Claim {action.lower()}ed successfully"})

@expense_bp.route("/budget-utilization", methods=['GET'])
@token_required
def expense_budget():
    # Only Management should see budget utilization
    if not is_management():
        return jsonify({"success": True, "data": []})

    return jsonify({
        "success": True,
        "data": [
            {"department": "Marketing Dept", "utilization": 80},
            {"department": "Sales Operations", "utilization": 42}
        ]
    })
