from datetime import datetime
from flask import Blueprint, request, jsonify, g, send_file
from models import db
from utils.decorators import token_required
from utils.rbac import require_roles
from utils.payslip_pdf import generate_payslip_pdf

from models.payroll import (
    PayGrade, PayRole, Payslip,
    PayslipEarning, PayslipDeduction, PayslipEmployerContribution, PayslipReimbursement
)

payroll_bp = Blueprint("payroll", __name__)

def _company_id():
    return g.user.company_id

def _employee_db_id():
    if hasattr(g.user, "employee_profile") and g.user.employee_profile:
        return g.user.employee_profile.id
    return None

def _is_owner_employee(payslip: Payslip):
    emp_id = _employee_db_id()
    return g.user.role == "EMPLOYEE" and emp_id == payslip.employee_id

def _replace_items(model, payslip_id, items):
    model.query.filter_by(payslip_id=payslip_id).delete()
    for it in items:
        component = (it.get("component") or "").strip()
        amount = float(it.get("amount", 0) or 0)
        if component:
            db.session.add(model(payslip_id=payslip_id, component=component, amount=amount))


# =========================================================
# PAYGRADE
# Super Admin: ONLY VIEW (+ optional PDF later if needed)
# Admin: manage pay grade? -> usually NO. So view only.
# =========================================================

@payroll_bp.route("/paygrades", methods=["GET"])
@token_required
@require_roles("SUPER_ADMIN", "ADMIN")
def list_paygrades():
    q = PayGrade.query
    if g.user.role != "SUPER_ADMIN":
        q = q.filter_by(company_id=_company_id())
    rows = q.order_by(PayGrade.id.desc()).all()
    return jsonify({"success": True, "data": [
        {
            "id": r.id,
            "company_id": r.company_id,
            "grade_name": r.grade_name,
            "min_salary": r.min_salary,
            "max_salary": r.max_salary,
            "basic_pct": r.basic_pct,
            "hra_pct": r.hra_pct,
            "ta_pct": r.ta_pct,
            "medical_pct": r.medical_pct,
            "is_active": r.is_active
        } for r in rows
    ]})


# =========================================================
# PAY ROLES (optional - admin can view)
# =========================================================

@payroll_bp.route("/payroles", methods=["GET"])
@token_required
@require_roles("ADMIN", "SUPER_ADMIN")
def list_payroles():
    q = PayRole.query
    if g.user.role != "SUPER_ADMIN":
        q = q.filter_by(company_id=_company_id())
    rows = q.order_by(PayRole.id.desc()).all()
    return jsonify({"success": True, "data": [
        {"id": r.id, "company_id": r.company_id, "name": r.name, "pay_grade_id": r.pay_grade_id, "is_active": r.is_active}
        for r in rows
    ]})


# =========================================================
# PAYSLIPS
# Admin: create/edit/view + pdf
# Employee: view own + pdf
# Super Admin: (optional) can view all companies? but you didn’t ask.
# so Super Admin not given payslip access here.
# =========================================================

@payroll_bp.route("/payslips", methods=["GET"])
@token_required
@require_roles("ADMIN")
def list_payslips():
    employee_id = request.args.get("employee_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    q = Payslip.query.filter_by(company_id=_company_id(), is_deleted=False)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if month:
        q = q.filter_by(pay_month=month)
    if year:
        q = q.filter_by(pay_year=year)

    rows = q.order_by(Payslip.id.desc()).all()
    return jsonify({"success": True, "data": [
        {
            "id": p.id,
            "employee_id": p.employee_id,
            "pay_month": p.pay_month,
            "pay_year": p.pay_year,
            "total_days": p.total_days,
            "paid_days": p.paid_days,
            "gross_salary": p.gross_salary,
            "total_deductions": p.total_deductions,
            "net_salary": p.net_salary,
            "created_at": p.created_at.isoformat()
        } for p in rows
    ]})

@payroll_bp.route("/payslips/<int:payslip_id>", methods=["GET"])
@token_required
@require_roles("ADMIN", "EMPLOYEE")
def get_payslip(payslip_id):
    p = Payslip.query.filter_by(id=payslip_id, is_deleted=False).first()
    if not p:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    if p.company_id != _company_id():
        return jsonify({"success": False, "message": "Permission denied"}), 403

    if g.user.role == "EMPLOYEE" and not _is_owner_employee(p):
        return jsonify({"success": False, "message": "Permission denied"}), 403

    return jsonify({
        "success": True,
        "data": {
            "id": p.id,
            "company_id": p.company_id,
            "employee_id": p.employee_id,
            "pay_month": p.pay_month,
            "pay_year": p.pay_year,
            "pay_date": p.pay_date.isoformat() if p.pay_date else None,
            "total_days": p.total_days,
            "paid_days": p.paid_days,
            "lwp_days": p.lwp_days,
            "gross_salary": p.gross_salary,
            "total_deductions": p.total_deductions,
            "total_reimbursements": p.total_reimbursements,
            "net_salary": p.net_salary,
            "annual_ctc": p.annual_ctc,
            "monthly_ctc": p.monthly_ctc,
            "tax_regime": p.tax_regime,
            "section_80c": p.section_80c,
            "monthly_rent": p.monthly_rent,
            "city_type": p.city_type,
            "other_deductions": p.other_deductions,
            "calculated_tds": p.calculated_tds,
            "bank_account_no": p.bank_account_no,
            "uan_no": p.uan_no,
            "esi_account_no": p.esi_account_no,
            "status": p.status,
            "earnings": [{"component": x.component, "amount": x.amount} for x in p.earnings],
            "deductions": [{"component": x.component, "amount": x.amount} for x in p.deductions],
            "employer_contribs": [{"component": x.component, "amount": x.amount} for x in p.employer_contribs],
            "reimbursements": [{"component": x.component, "amount": x.amount} for x in p.reimbursements],
            "pdf_path": p.pdf_path
        }
    })

@payroll_bp.route("/payslips", methods=["POST"])
@token_required
@require_roles("ADMIN")
def create_payslip():
    data = request.get_json() or {}

    for f in ["employee_id", "pay_month", "pay_year"]:
        if data.get(f) is None:
            return jsonify({"success": False, "message": f"{f} is required"}), 400

    p = Payslip(
        company_id=_company_id(),
        employee_id=int(data["employee_id"]),
        pay_month=int(data["pay_month"]),
        pay_year=int(data["pay_year"]),
        total_days=int(data.get("total_days", 0) or 0),
        paid_days=int(data.get("paid_days", 0) or 0),
        lwp_days=int(data.get("lwp_days", 0) or 0),
        gross_salary=float(data.get("gross_salary", 0) or 0),
        total_deductions=float(data.get("total_deductions", 0) or 0),
        total_reimbursements=float(data.get("total_reimbursements", 0) or 0),
        net_salary=float(data.get("net_salary", 0) or 0),
        annual_ctc=float(data.get("annual_ctc", 0) or 0),
        monthly_ctc=float(data.get("monthly_ctc", 0) or 0),

        tax_regime=data.get("tax_regime", "OLD"),
        section_80c=float(data.get("section_80c", 0) or 0),
        monthly_rent=float(data.get("monthly_rent", 0) or 0),
        city_type=data.get("city_type", "NON_METRO"),
        other_deductions=float(data.get("other_deductions", 0) or 0),
        calculated_tds=float(data.get("calculated_tds", 0) or 0),

        bank_account_no=data.get("bank_account_no"),
        uan_no=data.get("uan_no"),
        esi_account_no=data.get("esi_account_no"),

        status=data.get("status", "DRAFT"),
        created_by=g.user.id
    )

    if data.get("pay_date"):
        p.pay_date = datetime.strptime(data["pay_date"], "%Y-%m-%d").date()

    db.session.add(p)
    db.session.flush()

    _replace_items(PayslipEarning, p.id, data.get("earnings", []))
    _replace_items(PayslipDeduction, p.id, data.get("deductions", []))
    _replace_items(PayslipEmployerContribution, p.id, data.get("employer_contribs", []))
    _replace_items(PayslipReimbursement, p.id, data.get("reimbursements", []))

    db.session.commit()
    return jsonify({"success": True, "message": "Payslip created", "id": p.id})

@payroll_bp.route("/payslips/<int:payslip_id>", methods=["PUT"])
@token_required
@require_roles("ADMIN")
def update_payslip(payslip_id):
    data = request.get_json() or {}
    p = Payslip.query.filter_by(id=payslip_id, company_id=_company_id(), is_deleted=False).first()
    if not p:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    for k in [
        "total_days","paid_days","lwp_days","gross_salary","total_deductions","total_reimbursements","net_salary",
        "annual_ctc","monthly_ctc","status",
        "tax_regime","section_80c","monthly_rent","city_type","other_deductions","calculated_tds",
        "bank_account_no","uan_no","esi_account_no"
    ]:
        if k in data:
            setattr(p, k, data[k])

    if "pay_date" in data and data["pay_date"]:
        p.pay_date = datetime.strptime(data["pay_date"], "%Y-%m-%d").date()

    if "earnings" in data: _replace_items(PayslipEarning, p.id, data["earnings"])
    if "deductions" in data: _replace_items(PayslipDeduction, p.id, data["deductions"])
    if "employer_contribs" in data: _replace_items(PayslipEmployerContribution, p.id, data["employer_contribs"])
    if "reimbursements" in data: _replace_items(PayslipReimbursement, p.id, data["reimbursements"])

    p.pdf_path = None
    db.session.commit()
    return jsonify({"success": True, "message": "Payslip updated"})

@payroll_bp.route("/my-payslips", methods=["GET"])
@token_required
@require_roles("EMPLOYEE")
def my_payslips():
    emp_id = _employee_db_id()
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile not linked"}), 400

    rows = Payslip.query.filter_by(company_id=_company_id(), employee_id=emp_id, is_deleted=False)\
        .order_by(Payslip.id.desc()).all()

    return jsonify({"success": True, "data": [
        {
            "id": p.id,
            "pay_month": p.pay_month,
            "pay_year": p.pay_year,
            "total_days": p.total_days,
            "paid_days": p.paid_days,
            "gross_salary": p.gross_salary,
            "total_deductions": p.total_deductions,
            "net_salary": p.net_salary,
            "created_at": p.created_at.isoformat()
        } for p in rows
    ]})

@payroll_bp.route("/payslips/<int:payslip_id>/pdf", methods=["GET"])
@token_required
@require_roles("ADMIN", "EMPLOYEE")
def download_payslip_pdf(payslip_id):
    p = Payslip.query.filter_by(id=payslip_id, is_deleted=False).first()
    if not p:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    if p.company_id != _company_id():
        return jsonify({"success": False, "message": "Permission denied"}), 403

    if g.user.role == "EMPLOYEE" and not _is_owner_employee(p):
        return jsonify({"success": False, "message": "Permission denied"}), 403

    if not p.pdf_path:
        p.pdf_path = generate_payslip_pdf(p)
        db.session.commit()

    return send_file(p.pdf_path, as_attachment=True)
