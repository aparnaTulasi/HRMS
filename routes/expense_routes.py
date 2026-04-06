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
import calendar

expense_bp = Blueprint("expenses", __name__)

def _company_id():
    return getattr(g, "company_id", 1)

def _user_id():
    return getattr(g, "user_id", None)

def _json_ok(data, message="Success"):
    return jsonify({"success": True, "data": data, "message": message})

@expense_bp.get("/stats")
@token_required
@permission_required("TRAVEL_AND_EXPENSES_VIEW")
def expense_stats():
    cid = _company_id()
    # 1. Total Expenses (YTD)
    current_year = date.today().year
    total_ytd = db.session.query(sa.func.sum(ExpenseClaim.amount)).filter(
        ExpenseClaim.company_id == cid,
        ExpenseClaim.status == "APPROVED",
        ExpenseClaim.year == current_year
    ).scalar() or 0
    
    # 2. Pending Claims
    pending_count = ExpenseClaim.query.filter_by(company_id=cid, status="PENDING").count()
    
    # 3. Approved Trips (Assumption: Flight/Hotel categories are trips)
    approved_trips = ExpenseClaim.query.filter(
        ExpenseClaim.company_id == cid,
        ExpenseClaim.status == "APPROVED",
        ExpenseClaim.category.in_(["Flight", "Hotel", "Taxi"])
    ).count()
    
    return _json_ok({
        "total_expenses_ytd": total_ytd,
        "pending_claims": pending_count,
        "approved_trips": approved_trips,
        "currency": "$"
    })

@expense_bp.get("/trends")
@token_required
@permission_required("TRAVEL_AND_EXPENSES_VIEW")
def expense_trends():
    cid = _company_id()
    trend = []
    now = date.today()
    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i*30)
        m = target_date.month
        y = target_date.year
        month_name = calendar.month_name[m][:3]
        
        monthly_sum = db.session.query(sa.func.sum(ExpenseClaim.amount)).filter(
            ExpenseClaim.company_id == cid,
            ExpenseClaim.status == "APPROVED",
            ExpenseClaim.month == m,
            ExpenseClaim.year == y
        ).scalar() or 0
        
        trend.append({"month": month_name, "amount": monthly_sum})
        
    return _json_ok(trend)

@expense_bp.get("/claims")
@token_required
@permission_required("TRAVEL_AND_EXPENSES_VIEW")
def expense_claims_list():
    items = ExpenseClaim.query.filter_by(company_id=_company_id()) \
        .order_by(ExpenseClaim.created_at.desc()).limit(20).all()
    return _json_ok([x.to_dict() for x in items])

@expense_bp.post("/claims")
@token_required
def expense_claim_submit():
    payload = request.get_json()
    e_date_str = payload.get("expense_date") # YYYY-MM-DD
    if not e_date_str:
        return jsonify({"success": False, "message": "Date is required"}), 400
        
    e_date = date.fromisoformat(e_date_str)
    now = datetime.now()
    
    user = g.get("user")
    
    claim = ExpenseClaim(
        company_id=_company_id(),
        employee_id=user.id if user else 1,
        project_purpose=payload.get("project_purpose", "Business Expense"),
        category=payload.get("category", "Others"),
        amount=float(payload.get("amount", 0)),
        currency=payload.get("currency", "$"),
        expense_date=e_date,
        description=payload.get("description"),
        status="PENDING",
        
        # Detailed fields requested
        year=e_date.year,
        month=e_date.month,
        day=e_date.day,
        time=now.strftime("%H:%M:%S"),
        added_by_name=user.full_name if user else "Unknown"
    )
    db.session.add(claim)
    db.session.commit()
    
    log_action(
        action="SUBMIT_EXPENSE_CLAIM",
        entity="ExpenseClaim",
        entity_id=claim.id,
        meta={"amount": claim.amount, "category": claim.category}
    )
    
    return _json_ok({"id": claim.id}, "Expense claim submitted")

@expense_bp.patch("/claims/<int:cid>/action")
@token_required
@permission_required(Permissions.EXPENSE_MANAGEMENT)
def expense_claim_action(cid):
    payload = request.get_json()
    action = payload.get("action") # APPROVE, REJECT
    
    claim = ExpenseClaim.query.get(cid)
    if not claim: return jsonify({"success": False, "message": "Not found"}), 404
        
    if action == "APPROVE":
        claim.status = "APPROVED"
        claim.approved_by = _user_id()
        claim.approved_at = datetime.utcnow()
    elif action == "REJECT":
        claim.status = "REJECTED"
        claim.rejection_reason = payload.get("reason")
        
    db.session.commit()
    
    log_action(
        action=f"EXPENSE_CLAIM_{action}",
        entity="ExpenseClaim",
        entity_id=cid
    )
    
    return _json_ok(None, f"Claim {action.lower()}ed")

@expense_bp.get("/budget-utilization")
@token_required
@permission_required(Permissions.EXPENSE_MANAGEMENT)
def expense_budget():
    # Mock data for UI as it depends on budgets not yet implemented
    return _json_ok([
        {"department": "Marketing Dept", "utilization": 80},
        {"department": "Sales Operations", "utilization": 42}
    ])
