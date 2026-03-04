import io
import re
import logging
from typing import cast, Any, Dict, List
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file, g
from models import db
from utils.decorators import token_required
from models.payroll import (
    PayGrade, PayRole, PaySlip, PayrollChangeRequest, SalaryStructureAssignment,
    PayslipEarning, PayslipDeduction, PayslipEmployerContribution, PayslipReimbursement,
    SalaryComponent, SalaryStructure, StructureComponent, StatutorySettings
)
from models.employee import Employee

payroll_bp = Blueprint("payroll_bp", __name__)


# -------------------------
# RBAC (Adapted for JWT/g.user)
# -------------------------
def require_roles(*roles):
    def decorator(fn):
        @token_required
        def wrapper(*args, **kwargs):
            role = getattr(g.user, "role", None)
            if role not in roles:
                return jsonify({"success": False, "message": "Forbidden"}), 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


def _company_id():
    cid = getattr(g.user, "company_id", None)
    if not cid:
        return None
    return int(cid)


def _sum_values(d: Any) -> float:
    if not d or not isinstance(d, dict):
        return 0.0
    total = 0.0
    for v in d.values():
        if v is None:
            continue
        try:
            val = float(v)
            total += val # pyre-ignore
        except (ValueError, TypeError):
            pass
    return round(total, 2)


def _populate_payslip_from_structure(ps: PaySlip):
    """
    Populates earnings/deductions of a payslip from the employee's assigned SalaryStructure.
    Requires ps.employee_id and ps.gross_salary (or base CTC) to be set.
    """
    assignment = SalaryStructureAssignment.query.filter_by(
        employee_id=ps.employee_id, is_active=True, status="ACTIVE"
    ).order_by(SalaryStructureAssignment.id.desc()).first()

    if not assignment or not assignment.salary_structure:
        return

    struct = assignment.salary_structure
    for sc in struct.components:
        comp = sc.component
        if not comp or comp.status != "ACTIVE":
            continue
        
        # Determine value (base component value or structure override)
        val = sc.override_value if sc.override_value is not None else comp.amount_value
        
        amount = 0.0
        if comp.calculation_type == "FLAT":
            amount = val
        elif comp.calculation_type == "PERCENT_OF_BASIC":
            # This requires a "Basic Salary" component to exist and be processed first.
            # For simplicity in this logic, we assume percent of monthly_ctc for now
            # unless we find the basic component.
            amount = (val / 100.0) * ps.monthly_ctc 
        elif comp.calculation_type == "PERCENT_OF_CTC":
            amount = (val / 100.0) * ps.monthly_ctc
        
        # Map component type to payslip relationship
        if comp.type == "EARNING":
            ps.earnings.append(PayslipEarning(component=comp.name, amount=amount))
        elif comp.type == "DEDUCTION" or comp.type == "STATUTORY_DEDUCTION":
            ps.deductions.append(PayslipDeduction(component=comp.name, amount=amount))
        elif comp.type == "EMPLOYER_CONTRIBUTION":
            ps.employer_contribs.append(PayslipEmployerContribution(component=comp.name, amount=amount))
        elif comp.type == "REIMBURSEMENT":
            ps.reimbursements.append(PayslipReimbursement(component=comp.name, amount=amount))


def _recalc_payslip(ps: PaySlip):
    ps.gross_salary = _sum_values(ps.earnings_dict)
    ps.total_deductions = _sum_values(ps.deductions_dict)
    ps.total_reimbursements = _sum_values(ps.reimbursements_dict)

    ps.net_salary = round(ps.gross_salary - ps.total_deductions + ps.total_reimbursements, 2)
    # monthly_ctc and annual_ctc logic might differ based on employer contributions
    # For now, keeping it simple:
    ps.monthly_ctc = round(ps.gross_salary + _sum_values(ps.employer_contrib_dict), 2)
    ps.annual_ctc = round(ps.monthly_ctc * 12, 2)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


# =========================================================
# SUPER ADMIN - PAY GRADE (VIEW + PDF ONLY)
# =========================================================
@payroll_bp.get("/superadmin/paygrades")
@require_roles("SUPER_ADMIN")
def superadmin_list_paygrades():
    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayGrade.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.get("/superadmin/paygrades/pdf")
@require_roles("SUPER_ADMIN")
def superadmin_paygrades_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayGrade.id.asc()).all()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "PayGrade Management")
    y -= 30

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Grade")
    c.drawString(150, y, "Salary Range")
    c.drawString(300, y, "Basic%")
    c.drawString(360, y, "HRA%")
    c.drawString(420, y, "TA%")
    c.drawString(470, y, "Medical%")
    y -= 15

    c.setFont("Helvetica", 10)
    for r in rows:
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

        c.drawString(50, y, r.grade_name)
        c.drawString(150, y, f"{r.min_salary:.2f} - {r.max_salary:.2f}")
        c.drawString(300, y, f"{r.basic_pct:.2f}")
        c.drawString(360, y, f"{r.hra_pct:.2f}")
        c.drawString(420, y, f"{r.ta_pct:.2f}")
        c.drawString(470, y, f"{r.medical_pct:.2f}")
        y -= 14

    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="paygrades.pdf")


# =========================================================
# ACCOUNT - PAYGRADE (CRUD + PDF)
# =========================================================
@payroll_bp.get("/account/paygrades")
@require_roles("ACCOUNT")
def account_list_paygrades():
    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayGrade.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/account/paygrades")
@require_roles("ACCOUNT")
def account_create_paygrade():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    grade_name = (data.get("grade_name") or "").strip()
    if not grade_name:
        return jsonify({"success": False, "message": "grade_name is required"}), 400

    row = PayGrade(
        company_id=cid,
        grade_name=grade_name,
        min_salary=float(data.get("min_salary", 0) or 0),
        max_salary=float(data.get("max_salary", 0) or 0),
        basic_pct=float(data.get("basic_percent", 50) or 50),
        hra_pct=float(data.get("hra_percent", 20) or 20),
        ta_pct=float(data.get("ta_percent", 10) or 10),
        medical_pct=float(data.get("medical_percent", 3) or 3),
        basic_percent=float(data.get("basic_percent", 50) or 50),
        hra_percent=float(data.get("hra_percent", 20) or 20),
        ta_percent=float(data.get("ta_percent", 10) or 10),
        medical_percent=float(data.get("medical_percent", 3) or 3),
    )
    db.session.add(row)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({"success": True, "data": row.to_dict()}), 201


@payroll_bp.put("/account/paygrades/<int:paygrade_id>")
@require_roles("ACCOUNT")
def account_update_paygrade(paygrade_id):
    cid = _company_id()
    row = PayGrade.query.filter_by(id=paygrade_id, company_id=cid, status="ACTIVE").first()
    if not row:
        return jsonify({"success": False, "message": "PayGrade not found"}), 404

    data = request.get_json(silent=True) or {}
    if "grade_name" in data:
        row.grade_name = (data["grade_name"] or "").strip()

    field_map = {
        "min_salary": "min_salary",
        "max_salary": "max_salary",
        "basic_percent": "basic_pct",
        "hra_percent": "hra_pct",
        "ta_percent": "ta_pct",
        "medical_percent": "medical_pct"
    }
    for f_in, f_out in field_map.items():
        if f_in in data:
            setattr(row, f_out, float(data[f_in] or 0))

    db.session.commit()
    return jsonify({"success": True, "data": row.to_dict()}), 200


@payroll_bp.delete("/account/paygrades/<int:paygrade_id>")
@require_roles("ACCOUNT")
def account_delete_paygrade(paygrade_id):
    cid = _company_id()
    row = PayGrade.query.filter_by(id=paygrade_id, company_id=cid, status="ACTIVE").first()
    if not row:
        return jsonify({"success": False, "message": "PayGrade not found"}), 404
    row.status = "DELETED"
    db.session.commit()
    return jsonify({"success": True, "message": "Deleted"}), 200


@payroll_bp.get("/account/paygrades/pdf")
@require_roles("ACCOUNT")
def account_paygrades_pdf():
    # reuse superadmin pdf function output
    return superadmin_paygrades_pdf()


# =========================================================
# ACCOUNT - PAY ROLES (CRUD)
# =========================================================
@payroll_bp.get("/account/payroles")
@require_roles("ACCOUNT")
def account_list_payroles():
    cid = _company_id()
    rows = PayRole.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayRole.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/account/payroles")
@require_roles("ACCOUNT")
def account_create_payrole():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "name is required"}), 400

    row = PayRole(
        company_id=cid,
        name=name,
        pay_grade_id=data.get("pay_grade_id"),
        earnings_template=data.get("earnings_template") or {},
        deductions_template=data.get("deductions_template") or {},
        employer_contribution_template=data.get("employer_contribution_template") or {},
        reimbursements_template=data.get("reimbursements_template") or {},
    )

    db.session.add(row)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({"success": True, "data": row.to_dict()}), 201


@payroll_bp.put("/account/payroles/<int:payrole_id>")
@require_roles("ACCOUNT")
def account_update_payrole(payrole_id):
    cid = _company_id()
    row = PayRole.query.filter_by(id=payrole_id, company_id=cid, status="ACTIVE").first()
    if not row:
        return jsonify({"success": False, "message": "PayRole not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        row.name = (data["name"] or "").strip()
    if "pay_grade_id" in data:
        row.pay_grade_id = data["pay_grade_id"]

    for f in ["earnings_template", "deductions_template", "employer_contribution_template", "reimbursements_template"]:
        if f in data and isinstance(data[f], dict):
            setattr(row, f, data[f])

    db.session.commit()
    return jsonify({"success": True, "data": row.to_dict()}), 200


@payroll_bp.delete("/account/payroles/<int:payrole_id>")
@require_roles("ACCOUNT")
def account_delete_payrole(payrole_id):
    cid = _company_id()
    row = PayRole.query.filter_by(id=payrole_id, company_id=cid, status="ACTIVE").first()
    if not row:
        return jsonify({"success": False, "message": "PayRole not found"}), 404
    row.status = "DELETED"
    db.session.commit()
    return jsonify({"success": True, "message": "Deleted"}), 200


# =========================================================
# ADMIN - PAY SLIP (CRUD + PDF)
# =========================================================
@payroll_bp.get("/admin/payslips")
@require_roles("ADMIN")
def admin_list_payslips():
    cid = _company_id()
    employee_id = request.args.get("employee_id", type=int)
    department_id = request.args.get("department_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    q = PaySlip.query.filter_by(company_id=cid, status="ACTIVE")
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if department_id:
        q = q.filter_by(department_id=department_id)
    if month:
        q = q.filter_by(pay_month=month)
    if year:
        q = q.filter_by(pay_year=year)

    rows = q.order_by(PaySlip.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/admin/payslips")
@require_roles("ADMIN")
def admin_create_payslip():
    cid = _company_id()
    data: dict = request.get_json(silent=True) or {}

    for k in ["employee_id", "pay_month", "pay_year"]:
        if not data.get(k):
            return jsonify({"success": False, "message": f"{k} is required"}), 400

    pay_date = _parse_date(data.get("pay_date"))
    if data.get("pay_date") and not pay_date:
        return jsonify({"success": False, "message": "pay_date must be YYYY-MM-DD"}), 400

    ps = PaySlip(
        company_id=cid,
        employee_id=int(data["employee_id"]),
        department_id=data.get("department_id"),
        pay_role_id=data.get("pay_role_id"),
        pay_month=int(data["pay_month"]),
        pay_year=int(data["pay_year"]),
        total_days=int(data.get("total_days", 30) or 30),
        paid_days=int(data.get("paid_days", 30) or 30),
        lwp_days=int(data.get("lwp_days", 0) or 0),
        pay_date=pay_date,
        bank_account_no=data.get("bank_account_number"),
        uan_no=data.get("uan_number"),
        esi_account_no=data.get("esi_account_number"),
        tax_regime=data.get("tax_regime", "Old Regime"),
        section_80c=float(data.get("section_80c", 0) or 0),
        monthly_rent=float(data.get("monthly_rent", 0) or 0),
        city_type=data.get("city_type", "Non-Metro"),
        other_deductions=float(data.get("other_deductions", 0) or 0),
        calculated_tds=float(data.get("calculated_tds", 0) or 0),
        pf_employee_pct=float(data.get("pf_employee_percent", 12) or 12),
        pf_employer_pct=float(data.get("pf_employer_percent", 12) or 12),
        esi_employee_pct=float(data.get("esi_employee_percent", 0.75) or 0.75),
        esi_employer_pct=float(data.get("esi_employer_percent", 3.25) or 3.25),
        created_by=getattr(g.user, "id", None),
    )

    # Relationships
    for comp, amt in (data.get("earnings") or {}).items():
        ps.earnings.append(PayslipEarning(component=comp, amount=float(amt)))
    for comp, amt in (data.get("deductions") or {}).items():
        ps.deductions.append(PayslipDeduction(component=comp, amount=float(amt)))
    for comp, amt in (data.get("employer_contribution") or {}).items():
        ps.employer_contribs.append(PayslipEmployerContribution(component=comp, amount=float(amt)))
    for comp, amt in (data.get("reimbursements") or {}).items():
        ps.reimbursements.append(PayslipReimbursement(component=comp, amount=float(amt)))

    _recalc_payslip(ps)

    db.session.add(ps)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({"success": True, "data": ps.to_dict()}), 201


@payroll_bp.post("/admin/payslips/generate")
@require_roles("ADMIN")
def admin_generate_payslip():
    cid = _company_id()
    data = request.get_json(silent=True) or {}
    
    emp_id = data.get("employee_id")
    month = data.get("pay_month")
    year = data.get("pay_year")
    
    if not emp_id or not month or not year:
        return jsonify({"success": False, "message": "employee_id, pay_month, and pay_year are required"}), 400
        
    # Check if exists
    try:
        m_int = int(str(month))
        y_int = int(str(year))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "pay_month and pay_year must be numbers"}), 400

    existing = PaySlip.query.filter_by(
        employee_id=emp_id, pay_month=m_int, pay_year=y_int, 
        company_id=cid, is_deleted=False
    ).first()
    if existing:
        return jsonify({"success": False, "message": "Payslip already exists for this period"}), 400
        
    employee = Employee.query.get(emp_id)
    if not employee or employee.company_id != cid:
        return jsonify({"success": False, "message": "Employee not found"}), 404
        
    ps = PaySlip(
        company_id=cid,
        employee_id=emp_id,
        pay_month=m_int,
        pay_year=y_int,
        status="DRAFT",
        created_by=getattr(g.user, "id", None)
    )
    
    # Base ctc logic: use employee ctc field
    ps.annual_ctc = float(employee.ctc or 0)
    ps.monthly_ctc = round(ps.annual_ctc / 12.0, 2)
    
    _populate_payslip_from_structure(ps)
    _recalc_payslip(ps)
    
    db.session.add(ps)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    
    return jsonify({"success": True, "data": ps.to_dict()}), 201


@payroll_bp.get("/admin/payslips/<int:payslip_id>")
@require_roles("ADMIN")
def admin_get_payslip(payslip_id):
    cid = _company_id()
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404
    return jsonify({"success": True, "data": ps.to_dict()}), 200


@payroll_bp.put("/admin/payslips/<int:payslip_id>")
@require_roles("ADMIN")
def admin_update_payslip(payslip_id):
    cid = _company_id()
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    data = (request.get_json(silent=True) or {})

    # simple fields
    for f in ["department_id", "pay_role_id", "total_days", "paid_days", "lwp_days"]:
        if data.get(f) is not None:
            val = data.get(f)
            setattr(ps, f, int(val or 0) if f in ["total_days", "paid_days", "lwp_days"] else val)

    if data.get("pay_date") is not None:
        pd = _parse_date(data.get("pay_date"))
        if data.get("pay_date") and not pd:
            return jsonify({"success": False, "message": "pay_date must be YYYY-MM-DD"}), 400
        ps.pay_date = pd

    # relational blocks
    if data.get("earnings") is not None and isinstance(data.get("earnings"), dict):
        ps.earnings = []
        for comp, amt in data["earnings"].items():
            ps.earnings.append(PayslipEarning(component=comp, amount=float(amt)))

    if data.get("deductions") is not None and isinstance(data.get("deductions"), dict):
        ps.deductions = []
        for comp, amt in data["deductions"].items():
            ps.deductions.append(PayslipDeduction(component=comp, amount=float(amt)))

    if data.get("employer_contribution") is not None and isinstance(data.get("employer_contribution"), dict):
        ps.employer_contribs = []
        for comp, amt in data["employer_contribution"].items():
            ps.employer_contribs.append(PayslipEmployerContribution(component=comp, amount=float(amt)))

    if data.get("reimbursements") is not None and isinstance(data.get("reimbursements"), dict):
        ps.reimbursements = []
        for comp, amt in data["reimbursements"].items():
            ps.reimbursements.append(PayslipReimbursement(component=comp, amount=float(amt)))

    # optional fields
    field_map = {
        "bank_account_number": "bank_account_no",
        "uan_number": "uan_no",
        "esi_account_number": "esi_account_no",
        "tax_regime": "tax_regime",
        "city_type": "city_type"
    }
    for f_in, f_out in field_map.items():
        if data.get(f_in) is not None:
            setattr(ps, f_out, data.get(f_in))

    for f in [
        "section_80c", "monthly_rent", "other_deductions", "calculated_tds",
        "pf_employee_percent", "pf_employer_percent", "esi_employee_percent", "esi_employer_percent"
    ]:
        if data.get(f) is not None:
            f_out = f.replace("percent", "pct") if "percent" in f else f
            setattr(ps, f_out, float(data.get(f) or 0))

    _recalc_payslip(ps)
    db.session.commit()
    return jsonify({"success": True, "data": ps.to_dict()}), 200


@payroll_bp.delete("/admin/payslips/<int:payslip_id>")
@require_roles("ADMIN")
def admin_delete_payslip(payslip_id):
    cid = _company_id()
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    ps.status = "DELETED"
    db.session.commit()
    return jsonify({"success": True, "message": "Deleted"}), 200


# =========================================================
# ACCOUNT - PAY SLIP (optional: allow ACCOUNT to manage too)
# =========================================================
@payroll_bp.get("/account/payslips")
@require_roles("ACCOUNT")
def account_list_payslips():
    # same as admin list
    return admin_list_payslips()


@payroll_bp.post("/account/payslips")
@require_roles("ACCOUNT")
def account_create_payslip():
    # same as admin create
    return admin_create_payslip()


@payroll_bp.put("/account/payslips/<int:payslip_id>")
@require_roles("ACCOUNT")
def account_update_payslip(payslip_id):
    # same as admin update
    return admin_update_payslip(payslip_id)


@payroll_bp.delete("/account/payslips/<int:payslip_id>")
@require_roles("ACCOUNT")
def account_delete_payslip(payslip_id):
    # same as admin delete
    return admin_delete_payslip(payslip_id)


# =========================================================
# EMPLOYEE - MY PAYSLIPS (READ ONLY + PDF)
# NOTE: your User should have employee_id OR use current_user.id
# =========================================================
@payroll_bp.get("/employee/payslips")
@require_roles("EMPLOYEE")
def employee_list_my_payslips():
    cid = _company_id()
    # Try to get employee_id from user object, or fallback to user.id if linked
    emp_id = None
    if hasattr(g.user, "employee_profile") and g.user.employee_profile:
        emp_id = g.user.employee_profile.id
    
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404

    rows = PaySlip.query.filter_by(company_id=cid, employee_id=int(emp_id), status="ACTIVE") \
        .order_by(PaySlip.id.desc()).all()

    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.get("/employee/payslips/<int:payslip_id>")
@require_roles("EMPLOYEE")
def employee_get_my_payslip(payslip_id):
    cid = _company_id()
    emp_id = None
    if hasattr(g.user, "employee_profile") and g.user.employee_profile:
        emp_id = g.user.employee_profile.id

    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404

    ps = PaySlip.query.filter_by(
        id=payslip_id, company_id=cid, employee_id=int(emp_id), status="ACTIVE"
    ).first()

    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    return jsonify({"success": True, "data": ps.to_dict()}), 200


# =========================================================
# PDF - for Admin + Employee + Account (same layout)
# =========================================================
@payroll_bp.get("/admin/payslips/<int:payslip_id>/pdf")
@require_roles("ADMIN")
def admin_payslip_pdf(payslip_id):
    cid = _company_id()
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404
    return _generate_payslip_pdf(ps, f"payslip_{ps.employee_id}_{ps.pay_month}-{ps.pay_year}.pdf")


@payroll_bp.get("/account/payslips/<int:payslip_id>/pdf")
@require_roles("ACCOUNT")
def account_payslip_pdf(payslip_id):
    cid = _company_id()
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404
    return _generate_payslip_pdf(ps, f"payslip_{ps.employee_id}_{ps.pay_month}-{ps.pay_year}.pdf")


@payroll_bp.get("/employee/payslips/<int:payslip_id>/pdf")
@require_roles("EMPLOYEE")
def employee_payslip_pdf(payslip_id):
    cid = _company_id()
    emp_id = None
    if hasattr(g.user, "employee_profile") and g.user.employee_profile:
        emp_id = g.user.employee_profile.id

    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404

    ps = PaySlip.query.filter_by(
        id=payslip_id, company_id=cid, employee_id=int(emp_id), status="ACTIVE"
    ).first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404

    return _generate_payslip_pdf(ps, f"payslip_{ps.pay_month}-{ps.pay_year}.pdf")


def _generate_payslip_pdf(ps: PaySlip, download_name: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Salary Slip")
    y -= 22

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Employee ID: {ps.employee_id}")
    c.drawString(250, y, f"Month/Year: {ps.pay_month:02d}/{ps.pay_year}")
    y -= 14
    c.drawString(50, y, f"Total Days: {ps.total_days}")
    c.drawString(150, y, f"Paid Days: {ps.paid_days}")
    c.drawString(250, y, f"LWP Days: {ps.lwp_days}")
    y -= 14
    c.drawString(50, y, f"Pay Date: {ps.pay_date.isoformat() if ps.pay_date else '-'}")
    y -= 24

    def section(title, data_dict):
        local_y = [y]  # Use list for mutable scoping
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, local_y[0], title)
        local_y[0] -= 14
        c.setFont("Helvetica", 10)

        if not data_dict:
            c.drawString(60, local_y[0], "-")
            local_y[0] -= 14
            return local_y[0]

        for k, v in data_dict.items():
            if local_y[0] < 80:
                c.showPage()
                local_y[0] = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(60, local_y[0], str(k))
            try:
                c.drawRightString(520, local_y[0], f"{float(v or 0):.2f}")
            except Exception:
                c.drawRightString(520, local_y[0], "0.00")
            local_y[0] -= 12
        local_y[0] -= 10
        return local_y[0]

    y = section("Earnings", ps.earnings_dict if hasattr(ps, 'earnings_dict') else {})
    y = section("Deductions", ps.deductions_dict if hasattr(ps, 'deductions_dict') else {})
    y = section("Employer Contribution", ps.employer_contrib_dict if hasattr(ps, 'employer_contrib_dict') else {})
    y = section("Reimbursements", ps.reimbursements_dict if hasattr(ps, 'reimbursements_dict') else {})

    if y < 130:
        c.showPage()
        y = height - 50

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Summary")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Total Earnings: {ps.total_earnings:.2f}")
    y -= 14
    c.drawString(60, y, f"Total Deductions: {ps.total_deductions:.2f}")
    y -= 14
    c.drawString(60, y, f"Total Reimbursement: {ps.total_reimbursements:.2f}")
    y -= 16
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, f"Net Salary: {ps.net_salary:.2f}")

    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=download_name)


# =========================================================
# OPTIONAL: ACCOUNT - SEND CHANGE REQUESTS
# =========================================================
@payroll_bp.post("/account/payroll/requests")
@require_roles("ACCOUNT")
def account_create_payroll_request():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    entity_type = (data.get("entity_type") or "").strip().upper()
    action = (data.get("action") or "").strip().upper()
    payload = data.get("payload") or {}
    entity_id = data.get("entity_id")

    if entity_type not in ["PAY_GRADE", "PAY_ROLE", "PAY_SLIP"]:
        return jsonify({"success": False, "message": "entity_type must be PAY_GRADE/PAY_ROLE/PAY_SLIP"}), 400
    if action not in ["CREATE", "UPDATE", "DELETE"]:
        return jsonify({"success": False, "message": "action must be CREATE/UPDATE/DELETE"}), 400
    if action in ["UPDATE", "DELETE"] and not entity_id:
        return jsonify({"success": False, "message": "entity_id is required for UPDATE/DELETE"}), 400

    req_row = PayrollChangeRequest(
        company_id=cid,
        entity_type=entity_type,
        action=action,
        entity_id=entity_id,
        payload=payload,
        requested_by=getattr(g.user, "id", None),
    )
    db.session.add(req_row)
    db.session.commit()
    return jsonify({"success": True, "data": req_row.to_dict()}), 201


@payroll_bp.get("/superadmin/payroll/requests")
@require_roles("SUPER_ADMIN")
def superadmin_list_requests():
    cid = _company_id()
    rows = PayrollChangeRequest.query.filter_by(company_id=cid).order_by(PayrollChangeRequest.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.get("/admin/payroll/requests")
@require_roles("ADMIN")
def admin_list_requests():
    cid = _company_id()
    rows = PayrollChangeRequest.query.filter_by(company_id=cid).order_by(PayrollChangeRequest.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/superadmin/payroll/requests/<int:req_id>/approve")
@require_roles("SUPER_ADMIN")
def superadmin_approve_request(req_id):
    # Superadmin typically approves paygrade/payrole requests
    cid = _company_id()
    req_row = PayrollChangeRequest.query.filter_by(id=req_id, company_id=cid).first()
    if not req_row:
        return jsonify({"success": False, "message": "Request not found"}), 404
    if req_row.status != "PENDING":
        return jsonify({"success": False, "message": "Request already processed"}), 400

    # apply only for PAY_GRADE / PAY_ROLE
    if req_row.entity_type not in ["PAY_GRADE", "PAY_ROLE"]:
        return jsonify({"success": False, "message": "Superadmin approves only PAY_GRADE/PAY_ROLE"}), 400

    _apply_request(req_row)
    req_row.status = "APPROVED"
    req_row.approved_by = getattr(g.user, "id", None)
    req_row.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Approved", "data": req_row.to_dict()}), 200


@payroll_bp.post("/admin/payroll/requests/<int:req_id>/approve")
@require_roles("ADMIN")
def admin_approve_request(req_id):
    # Admin typically approves payslip requests
    cid = _company_id()
    req_row = PayrollChangeRequest.query.filter_by(id=req_id, company_id=cid).first()
    if not req_row:
        return jsonify({"success": False, "message": "Request not found"}), 404
    if req_row.status != "PENDING":
        return jsonify({"success": False, "message": "Request already processed"}), 400

    if req_row.entity_type != "PAY_SLIP":
        return jsonify({"success": False, "message": "Admin approves only PAY_SLIP"}), 400

    _apply_request(req_row)
    req_row.status = "APPROVED"
    req_row.approved_by = getattr(g.user, "id", None)
    req_row.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Approved", "data": req_row.to_dict()}), 200


def _apply_request(req_row: PayrollChangeRequest):
    # Applies request payload to DB
    payload = req_row.payload or {}
    cid = req_row.company_id

    if req_row.entity_type == "PAY_GRADE":
        if req_row.action == "CREATE":
            row = PayGrade(company_id=cid, **payload)
            db.session.add(row)
        elif req_row.action == "UPDATE":
            row = PayGrade.query.filter_by(id=req_row.entity_id, company_id=cid, status="ACTIVE").first()
            if row:
                for k, v in payload.items():
                    setattr(row, k, v)
        elif req_row.action == "DELETE":
            row = PayGrade.query.filter_by(id=req_row.entity_id, company_id=cid, status="ACTIVE").first()
            if row:
                row.status = "DELETED"

    if req_row.entity_type == "PAY_ROLE":
        if req_row.action == "CREATE":
            row = PayRole(company_id=cid, **payload)
            db.session.add(row)
        elif req_row.action == "UPDATE":
            row = PayRole.query.filter_by(id=req_row.entity_id, company_id=cid, status="ACTIVE").first()
            if row:
                for k, v in payload.items():
                    setattr(row, k, v)
        elif req_row.action == "DELETE":
            row = PayRole.query.filter_by(id=req_row.entity_id, company_id=cid, status="ACTIVE").first()
            if row:
                row.status = "DELETED"

    if req_row.entity_type == "PAY_SLIP":
        if req_row.action == "CREATE":
            row = PaySlip(company_id=cid, **payload)
            _recalc_payslip(row)
            db.session.add(row)
        elif req_row.action == "UPDATE":
            row = PaySlip.query.filter_by(id=req_row.entity_id, company_id=cid, status="ACTIVE").first()
            if row:
                for k, v in payload.items():
                    setattr(row, k, v)
                _recalc_payslip(row)
        elif req_row.action == "DELETE":
            row = PaySlip.query.filter_by(id=req_row.entity_id, company_id=cid, status="ACTIVE").first()
            if row:
                row.status = "DELETED"


# =========================================================
# SALARY STRUCTURE ASSIGNMENT (Super Admin / Admin / Account)
# =========================================================
@payroll_bp.get("/superadmin/salary-assignments")
@require_roles("SUPER_ADMIN", "ADMIN", "ACCOUNT")
def list_salary_assignments():
    cid = _company_id()
    rows = SalaryStructureAssignment.query.filter_by(company_id=cid, status="ACTIVE").order_by(SalaryStructureAssignment.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/superadmin/salary-assignments")
@require_roles("SUPER_ADMIN", "ADMIN", "ACCOUNT")
def create_salary_assignment():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    emp_id = data.get("employee_id")
    grade_id = data.get("pay_grade_id") # Legacy
    struct_id = data.get("salary_structure_id") # New modular
    from_date_str = data.get("from_date")

    if not emp_id or not from_date_str:
        return jsonify({"success": False, "message": "employee_id and from_date are required"}), 400
    
    if not grade_id and not struct_id:
        return jsonify({"success": False, "message": "pay_grade_id or salary_structure_id is required"}), 400

    from_date = _parse_date(from_date_str)
    if not from_date:
        return jsonify({"success": False, "message": "Invalid from_date format (YYYY-MM-DD)"}), 400

    row = SalaryStructureAssignment(
        company_id=cid,
        employee_id=emp_id,
        pay_grade_id=grade_id,
        salary_structure_id=struct_id,
        from_date=from_date,
        created_by=getattr(g.user, "id", None)
    )
    db.session.add(row)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({"success": True, "data": row.to_dict()}), 201


# =========================================================
# SALARY COMPONENTS (NEW)
# =========================================================
@payroll_bp.get("/superadmin/payroll/components")
@require_roles("SUPER_ADMIN", "ADMIN")
def list_salary_components():
    cid = _company_id()
    rows = SalaryComponent.query.filter_by(company_id=cid, status="ACTIVE").all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200

@payroll_bp.post("/superadmin/payroll/components")
@require_roles("SUPER_ADMIN", "ADMIN")
def create_salary_component():
    cid = _company_id()
    data = request.get_json(silent=True) or {}
    
    comp = SalaryComponent(
        company_id=cid,
        name=data.get("name"),
        type=data.get("type"),
        calculation_type=data.get("calculation_type", "FLAT"),
        amount_value=float(data.get("amount_value", 0) or 0),
        is_taxable=bool(data.get("is_taxable", True)),
        is_statutory=bool(data.get("is_statutory", False)),
        is_part_of_ctc=bool(data.get("is_part_of_ctc", True)),
        frequency=data.get("frequency", "MONTHLY")
    )
    db.session.add(comp)
    db.session.commit()
    return jsonify({"success": True, "data": comp.to_dict()}), 201

@payroll_bp.delete("/superadmin/payroll/components/<int:comp_id>")
@require_roles("SUPER_ADMIN", "ADMIN")
def delete_salary_component(comp_id):
    cid = _company_id()
    comp = SalaryComponent.query.filter_by(id=comp_id, company_id=cid).first()
    if not comp:
        return jsonify({"success": False, "message": "Component not found"}), 404
    comp.status = "DELETED"
    db.session.commit()
    return jsonify({"success": True, "message": "Deleted"}), 200

# =========================================================
# SALARY STRUCTURES (NEW)
# =========================================================
@payroll_bp.get("/superadmin/payroll/structures")
@require_roles("SUPER_ADMIN", "ADMIN")
def list_salary_structures():
    cid = _company_id()
    rows = SalaryStructure.query.filter_by(company_id=cid, status="ACTIVE").all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200

@payroll_bp.post("/superadmin/payroll/structures")
@require_roles("SUPER_ADMIN", "ADMIN")
def create_salary_structure():
    cid = _company_id()
    data = request.get_json(silent=True) or {}
    
    struct = SalaryStructure(
        company_id=cid,
        name=data.get("name"),
        description=data.get("description")
    )
    db.session.add(struct)
    db.session.flush() # get struct.id
    
    components = data.get("components") or []
    for c in components:
        sc = StructureComponent(
            structure_id=struct.id,
            component_id=c.get("component_id"),
            override_value=c.get("override_value")
        )
        db.session.add(sc)
        
    db.session.commit()
    return jsonify({"success": True, "data": struct.to_dict()}), 201

# =========================================================
# STATUTORY SETTINGS (NEW)
# =========================================================
@payroll_bp.get("/superadmin/payroll/statutory")
@require_roles("SUPER_ADMIN", "ADMIN")
def get_statutory_settings():
    cid = _company_id()
    st = StatutorySettings.query.filter_by(company_id=cid).first()
    if not st:
        st = StatutorySettings(company_id=cid)
        db.session.add(st)
        db.session.commit()
    return jsonify({"success": True, "data": st.to_dict()}), 200

@payroll_bp.put("/superadmin/payroll/statutory")
@require_roles("SUPER_ADMIN", "ADMIN")
def update_statutory_settings():
    cid = _company_id()
    st = StatutorySettings.query.filter_by(company_id=cid).first()
    if not st:
        st = StatutorySettings(company_id=cid)
        db.session.add(st)
    
    data = request.get_json(silent=True) or {}
    st_dict = cast(dict, st.to_dict())
    
    for k in ["pf_employee_pct", "pf_employer_pct", "esi_employee_pct", "esi_employer_pct"]:
        if data.get(k) is not None: # pyre-ignore
            setattr(st, k, float(cast(Any, data[k]) or 0))
            
    for k in ["enable_pf", "enable_esi", "enable_tds"]:
        if data.get(k) is not None: # pyre-ignore
            setattr(st, k, bool(data[k]))
            
    db.session.commit()
    return jsonify({"success": True, "data": st.to_dict()}), 200

# =========================================================
# UPDATED HELPERS
# =========================================================
@payroll_bp.get("/superadmin/employees-dropdown")
@require_roles("SUPER_ADMIN", "ADMIN", "ACCOUNT")
def list_employees_dropdown():
    cid = _company_id()
    rows = Employee.query.filter_by(company_id=cid).all()
    data = [{"id": r.id, "name": r.full_name, "employee_id": r.employee_id} for r in rows]
    return jsonify({"success": True, "data": data}), 200


@payroll_bp.get("/superadmin/paygrades-dropdown")
@require_roles("SUPER_ADMIN", "ADMIN", "ACCOUNT")
def list_paygrades_dropdown():
    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").all()
    data = [{"id": r.id, "grade_name": r.grade_name} for r in rows]
    return jsonify({"success": True, "data": data}), 200

@payroll_bp.get("/superadmin/structures-dropdown")
@require_roles("SUPER_ADMIN", "ADMIN", "ACCOUNT")
def list_structures_dropdown():
    cid = _company_id()
    rows = SalaryStructure.query.filter_by(company_id=cid, status="ACTIVE").all()
    data = [{"id": r.id, "name": r.name} for r in rows]
    return jsonify({"success": True, "data": data}), 200

@payroll_bp.get("/superadmin/components-dropdown")
@require_roles("SUPER_ADMIN", "ADMIN", "ACCOUNT")
def list_components_dropdown():
    cid = _company_id()
    rows = SalaryComponent.query.filter_by(company_id=cid, status="ACTIVE").all()
    data = [{"id": r.id, "name": r.name, "type": r.type} for r in rows]
    return jsonify({"success": True, "data": data}), 200
