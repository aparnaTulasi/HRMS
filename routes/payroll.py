import io
import re
import logging
from typing import cast, Any, Dict, List
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file, g
from models import db
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from utils.date_utils import parse_date
from models.payroll import (
    PayGrade, PayRole, PaySlip, PayrollChangeRequest, SalaryStructureAssignment,
    PayslipEarning, PayslipDeduction, PayslipEmployerContribution, PayslipReimbursement,
    SalaryComponent, SalaryStructure, StructureComponent, StatutorySettings
)
from models.employee import Employee
from models.user import User
from models.company import Company
from models.attendance import Attendance
from models.employee_statutory import Form16, FullAndFinal, PayrollLetter
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocument
import calendar
from sqlalchemy import or_, func, and_

payroll_bp = Blueprint("payroll_bp", __name__)


# -------------------------
# RBAC (Adapted for JWT/g.user)
# -------------------------


def _company_id():
    # If provided in query params and user is authorized, use it
    req_cid = request.args.get("company_id")
    if req_cid and g.user.role == "SUPER_ADMIN":
        return int(req_cid)
    
    cid = getattr(g.user, "company_id", None)
    if not cid:
        return None
    return int(cid)


def _get_attendance_summary(employee_id, month, year):
    """
    Returns (total_days, lwp_days, paid_days)
    """
    _, last_day = calendar.monthrange(year, month)
    total_days = last_day
    
    # Count Absents and Half Days
    absent_count = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.month == month,
        Attendance.year == year,
        Attendance.status.in_(["Absent", "LWP"])
    ).count()
    
    half_day_count = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.month == month,
        Attendance.year == year,
        Attendance.status.in_(["Half Day", "Half-Day"])
    ).count()
    
    lwp_days = float(absent_count) + (float(half_day_count) * 0.5)
    paid_days = float(total_days) - lwp_days
    return total_days, lwp_days, paid_days


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
    
    total_days = ps.total_days or 30
    paid_days = ps.paid_days if ps.paid_days is not None else total_days
    prorate_factor = paid_days / total_days if total_days > 0 else 1.0

    # First pass: find Basic Salary amount
    basic_amount = ps.monthly_ctc # Fallback
    for sc in struct.components:
        if sc.component and sc.component.name.upper() == "BASIC":
            val = sc.override_value if sc.override_value is not None else sc.component.amount_value
            basic_amount = val * prorate_factor
            break

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
            amount = (val / 100.0) * (basic_amount / prorate_factor if prorate_factor > 0 else basic_amount)
        elif comp.calculation_type == "PERCENT_OF_CTC":
            amount = (val / 100.0) * ps.monthly_ctc
        
        # Apply Prorating for earnings/deductions if applicable
        if comp.type in ["EARNING"] and comp.is_prorated:
            amount = amount * prorate_factor

        # Map component type to payslip relationship
        if comp.type == "EARNING":
            ps.earnings.append(PayslipEarning(component=comp.name, amount=round(amount, 2)))
        elif comp.type == "DEDUCTION" or comp.type == "STATUTORY_DEDUCTION":
            ps.deductions.append(PayslipDeduction(component=comp.name, amount=round(amount, 2)))
        elif comp.type == "EMPLOYER_CONTRIBUTION":
            ps.employer_contribs.append(PayslipEmployerContribution(component=comp.name, amount=round(amount, 2)))
        elif comp.type == "REIMBURSEMENT":
            ps.reimbursements.append(PayslipReimbursement(component=comp.name, amount=round(amount, 2)))


def _recalc_payslip(ps: PaySlip):
    # Sum up current manually entered/populated values
    earnings_total = _sum_values(ps.earnings_dict)
    
    # 1. Handle Statutory Calculations automatically if flags are set
    # Find Basic Earning for base calculations
    basic_amt = 0.0
    for e in ps.earnings:
        if e.component.upper() == "BASIC":
            basic_amt = e.amount
            break
    
    if basic_amt > 0:
        # Update PF Employee if in deductions
        for d in ps.deductions:
            if d.component.upper() in ["PF", "PF EMPLOYEE", "PROVIDENT FUND"]:
                d.amount = round((ps.pf_employee_pct / 100.0) * basic_amt, 2)
        
        # Update ESI Employee if in deductions
        for d in ps.deductions:
            if d.component.upper() in ["ESI", "ESI EMPLOYEE"]:
                if basic_amt <= 21000: # Standard ESI limit, but we calculate if present
                    d.amount = round((ps.esi_employee_pct / 100.0) * basic_amt, 2)
        
        # Update Employer Contributions
        for c in ps.employer_contribs:
            if c.component.upper() in ["PF", "PF EMPLOYER"]:
                c.amount = round((ps.pf_employer_pct / 100.0) * basic_amt, 2)
            if c.component.upper() in ["ESI", "ESI EMPLOYER"]:
                c.amount = round((ps.esi_employer_pct / 100.0) * basic_amt, 2)

    ps.gross_salary = _sum_values(ps.earnings_dict)
    ps.total_deductions = _sum_values(ps.deductions_dict)
    ps.total_reimbursements = _sum_values(ps.reimbursements_dict)

    ps.net_salary = round(ps.gross_salary - ps.total_deductions + ps.total_reimbursements, 2)
    # monthly_ctc includes employer contributions
    ps.monthly_ctc = round(ps.gross_salary + _sum_values(ps.employer_contrib_dict), 2)
    ps.annual_ctc = round(ps.monthly_ctc * 12, 2)


# _parse_date removed to use central parse_date


# =========================================================
# SUPER ADMIN - PAY GRADE (VIEW + PDF ONLY)
# =========================================================
@payroll_bp.get("/superadmin/paygrades")
@permission_required("PAYROLL_VIEW")
def superadmin_list_paygrades():
    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayGrade.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.get("/superadmin/paygrades/pdf")
@permission_required("PAYROLL_EXPORT")
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
@permission_required(Permissions.PAYROLL_VIEW)
def account_list_paygrades():
    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayGrade.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/account/paygrades")
@permission_required(Permissions.PAYROLL_CREATE)
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
@permission_required(Permissions.PAYROLL_EDIT)
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
@permission_required(Permissions.PAYROLL_EDIT)
def account_delete_paygrade(paygrade_id):
    cid = _company_id()
    row = PayGrade.query.filter_by(id=paygrade_id, company_id=cid, status="ACTIVE").first()
    if not row:
        return jsonify({"success": False, "message": "PayGrade not found"}), 404
    row.status = "DELETED"
    db.session.commit()
    return jsonify({"success": True, "message": "Deleted"}), 200


@payroll_bp.get("/account/paygrades/pdf")
@permission_required(Permissions.PAYROLL_VIEW)
def account_paygrades_pdf():
    # reuse superadmin pdf function output
    return superadmin_paygrades_pdf()


# =========================================================
# ACCOUNT - PAY ROLES (CRUD)
# =========================================================
@payroll_bp.get("/account/payroles")
@permission_required(Permissions.PAYROLL_VIEW)
def account_list_payroles():
    cid = _company_id()
    rows = PayRole.query.filter_by(company_id=cid, status="ACTIVE").order_by(PayRole.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/account/payroles")
@permission_required(Permissions.PAYROLL_CREATE)
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
@permission_required(Permissions.PAYROLL_EDIT)
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
@permission_required(Permissions.PAYROLL_EDIT)
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
@permission_required(Permissions.PAYROLL_VIEW)
def admin_list_payslips():
    cid = _company_id()
    user_role = getattr(g.user, "role", "EMPLOYEE")
    
    employee_id = request.args.get("employee_id", type=int)
    department_id = request.args.get("department_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    q = PaySlip.query.filter_by(company_id=cid, status="ACTIVE")
    
    if user_role == "HR":
        # HR can only see Manager and Employee payslips
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))

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
@permission_required(Permissions.PAYROLL_CREATE)
def admin_create_payslip():
    cid = _company_id()
    data: dict = request.get_json(silent=True) or {}

    for k in ["employee_id", "pay_month", "pay_year"]:
        if not data.get(k):
            return jsonify({"success": False, "message": f"{k} is required"}), 400

    pay_date = parse_date(data.get("pay_date"))
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
    )

    # Fetch Statutory Defaults
    st = StatutorySettings.query.filter_by(company_id=cid).first()
    ps.pf_employee_pct = float(data.get("pf_employee_percent") or (st.pf_employee_pct if st else 12))
    ps.pf_employer_pct = float(data.get("pf_employer_percent") or (st.pf_employer_pct if st else 12))
    ps.esi_employee_pct = float(data.get("esi_employee_percent") or (st.esi_employee_pct if st else 0.75))
    ps.esi_employer_pct = float(data.get("esi_employer_percent") or (st.esi_employer_pct if st else 3.25))

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
@permission_required(Permissions.PAYROLL_GENERATE)
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

    # Fetch Statutory Defaults for Generate
    st = StatutorySettings.query.filter_by(company_id=cid).first()
    ps.pf_employee_pct = st.pf_employee_pct if st else 12
    ps.pf_employer_pct = st.pf_employer_pct if st else 12
    ps.esi_employee_pct = st.esi_employee_pct if st else 0.75
    ps.esi_employer_pct = st.esi_employer_pct if st else 3.25
    
    # Automatic attendance summary
    total, lwp, paid = _get_attendance_summary(emp_id, m_int, y_int)
    ps.total_days = total
    ps.lwp_days = lwp
    ps.paid_days = paid

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
@permission_required(Permissions.PAYROLL_VIEW)
def admin_get_payslip(payslip_id):
    cid = _company_id()
    user_role = getattr(g.user, "role", "EMPLOYEE")
    
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404
    
    if user_role == "HR":
        employee = Employee.query.get(ps.employee_id)
        if not employee or not employee.user or employee.user.role not in ["MANAGER", "EMPLOYEE"]:
            return jsonify({"success": False, "message": "Access Forbidden to this record"}), 403
            
    return jsonify({"success": True, "data": ps.to_dict()}), 200


@payroll_bp.put("/admin/payslips/<int:payslip_id>")
@permission_required(Permissions.PAYROLL_EDIT)
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
        pd = parse_date(data.get("pay_date"))
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
@permission_required(Permissions.PAYROLL_EDIT)
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
@permission_required(Permissions.PAYROLL_VIEW)
def account_list_payslips():
    # same as admin list
    return admin_list_payslips()


@payroll_bp.post("/account/payslips")
@permission_required(Permissions.PAYROLL_CREATE)
def account_create_payslip():
    # same as admin create
    return admin_create_payslip()


@payroll_bp.put("/account/payslips/<int:payslip_id>")
@permission_required(Permissions.PAYROLL_EDIT)
def account_update_payslip(payslip_id):
    # same as admin update
    return admin_update_payslip(payslip_id)


@payroll_bp.delete("/account/payslips/<int:payslip_id>")
@permission_required(Permissions.PAYROLL_EDIT)
def account_delete_payslip(payslip_id):
    # same as admin delete
    return admin_delete_payslip(payslip_id)


# =========================================================
# EMPLOYEE - MY PAYSLIPS (READ ONLY + PDF)
# NOTE: your User should have employee_id OR use current_user.id
# =========================================================
@payroll_bp.get("/employee/payslips")
@token_required
@permission_required("PAYROLL_VIEW")
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
@permission_required(Permissions.PAYROLL_VIEW)
def admin_payslip_pdf(payslip_id):
    cid = _company_id()
    user_role = getattr(g.user, "role", "EMPLOYEE")
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404
        
    if user_role == "HR":
        employee = Employee.query.get(ps.employee_id)
        if not employee or not employee.user or employee.user.role not in ["MANAGER", "EMPLOYEE"]:
            return jsonify({"success": False, "message": "Access Forbidden to this record"}), 403

    return _generate_payslip_pdf(ps, f"payslip_{ps.employee_id}_{ps.pay_month}-{ps.pay_year}.pdf")


@payroll_bp.get("/account/payslips/<int:payslip_id>/pdf")
@permission_required(Permissions.PAYROLL_VIEW)
def account_payslip_pdf(payslip_id):
    cid = _company_id()
    ps = PaySlip.query.filter_by(id=payslip_id, company_id=cid, status="ACTIVE").first()
    if not ps:
        return jsonify({"success": False, "message": "Payslip not found"}), 404
    return _generate_payslip_pdf(ps, f"payslip_{ps.employee_id}_{ps.pay_month}-{ps.pay_year}.pdf")


@payroll_bp.get("/employee/payslips/<int:payslip_id>/pdf")
@token_required
@permission_required("PAYROLL_EXPORT")
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


@payroll_bp.get("/employee/form16")
@token_required
def employee_list_my_form16():
    cid = _company_id()
    if not hasattr(g.user, "employee_profile") or not g.user.employee_profile:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404
    
    emp_id = g.user.employee_profile.id
    records = Form16.query.filter_by(employee_id=emp_id, company_id=cid).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in records]}), 200

@payroll_bp.get("/employee/form16/<int:form16_id>/pdf")
@token_required
def employee_form16_pdf(form16_id):
    cid = _company_id()
    if not hasattr(g.user, "employee_profile") or not g.user.employee_profile:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404
        
    emp_id = g.user.employee_profile.id
    record = Form16.query.filter_by(id=form16_id, employee_id=emp_id, company_id=cid).first()
    if not record:
        return jsonify({"success": False, "message": "Form-16 not found"}), 404
        
    return _generate_form16_pdf(record, f"form16_{record.fy}.pdf")

@payroll_bp.get("/employee/fnf")
@token_required
def employee_get_my_fnf():
    cid = _company_id()
    if not hasattr(g.user, "employee_profile") or not g.user.employee_profile:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404
        
    emp_id = g.user.employee_profile.id
    record = FullAndFinal.query.filter_by(employee_id=emp_id, company_id=cid).first()
    if not record:
        return jsonify({"success": False, "message": "F&F settlement details not found"}), 404
        
    return jsonify({"success": True, "data": record.to_dict()}), 200

@payroll_bp.get("/employee/fnf/<int:fnf_id>/pdf")
@token_required
def employee_fnf_pdf(fnf_id):
    cid = _company_id()
    if not hasattr(g.user, "employee_profile") or not g.user.employee_profile:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404
        
    emp_id = g.user.employee_profile.id
    record = FullAndFinal.query.filter_by(id=fnf_id, employee_id=emp_id, company_id=cid).first()
    if not record:
        return jsonify({"success": False, "message": "F&F settlement not found"}), 404
        
    # Restrict viewing if still in draft if necessary, but according to UI it seems fine
    return _generate_fnf_pdf(record, f"fnf_settlement.pdf")


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


def _generate_form16_pdf(record: Form16, download_name: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Form-16: Tax Certificate")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Financial Year: {record.fy}")
    c.drawString(200, y, f"Assessment Year: {record.ay}")
    y -= 14
    c.drawString(50, y, f"Employee Name: {record.employee.full_name if record.employee else 'N/A'}")
    y -= 14
    c.drawString(50, y, f"PAN of Employee: {record.pan or 'N/A'}")
    c.drawString(200, y, f"TAN of Employer: {record.tan or 'N/A'}")
    y -= 24

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Details of Tax Deducted at Source")
    y -= 15
    # Simplistic summary for now
    c.drawString(60, y, "Summary from Part B:")
    y -= 14
    c.setFont("Helvetica", 11)
    
    # Safely access Part B data
    part_b = record.part_b or {}
    gross_income = part_b.get("gross_income", 0.0)
    total_deductions = part_b.get("total_deductions", 0.0)
    taxable_income = part_b.get("taxable_income", 0.0)
    tax_on_income = part_b.get("tax_on_total_income", 0.0)

    c.drawString(70, y, f"1. Gross Salary: Rs {float(gross_income):,.2f}")
    y -= 14
    c.drawString(70, y, f"2. Total Deductions (Chapter VI-A): Rs {float(total_deductions):,.2f}")
    y -= 14
    c.drawString(70, y, f"3. Taxable Income: Rs {float(taxable_income):,.2f}")
    y -= 14
    c.setFont("Helvetica-Bold", 11)
    c.drawString(70, y, f"4. Net Tax Payable: Rs {float(tax_on_income):,.2f}")

    y -= 100
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "* This is a computer-generated summary of your Form-16 certificate.")

    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=download_name)


def _generate_fnf_pdf(record: FullAndFinal, download_name: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Full and Final Settlement Statement")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Employee: {record.employee.full_name if record.employee else 'N/A'}")
    c.drawString(300, y, f"Employee ID: {record.employee.employee_id if record.employee else 'N/A'}")
    y -= 14
    c.drawString(50, y, f"Last Working Day: {record.last_working_day.strftime('%d %b %Y') if record.last_working_day else '-'}")
    c.drawString(300, y, f"Department: {record.employee.department if record.employee else '-'}")
    y -= 24

    settlement = record.settlement_data or {}
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Settlement Summary")
    y -= 18
    c.setFont("Helvetica", 11)
    
    total_earnings = settlement.get("earnings", {}).get("total", 0.0)
    total_deductions = settlement.get("deductions", {}).get("total", 0.0)
    net_payable = float(total_earnings) - float(total_deductions)

    c.drawString(60, y, f"Total Earnings Payable: Rs {float(total_earnings):,.2f}")
    y -= 14
    c.drawString(60, y, f"Total Recovery/Deductions: Rs {float(total_deductions):,.2f}")
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, f"Net Settlement Amount: Rs {net_payable:,.2f}")
    
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Notice Period Required: {record.notice_period_required or 0} days")
    y -= 14
    c.drawString(50, y, f"Notice Period Served: {record.notice_period_served or 0} days")
    y -= 14
    c.drawString(50, y, f"Notice Status: {record.notice_status or 'N/A'}")

    y -= 100
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Settlement Status: " + (record.status.upper() if record.status else "PENDING"))

    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=download_name)


# =========================================================
# OPTIONAL: ACCOUNT - SEND CHANGE REQUESTS
# =========================================================
@payroll_bp.post("/account/payroll/requests")
@permission_required(Permissions.PAYROLL_CREATE)
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
        request_type=entity_type,
        employee_id=entity_id,
        payload=payload,
        requested_by=getattr(g.user, "id", None),
    )
    db.session.add(req_row)
    db.session.commit()
    return jsonify({"success": True, "data": req_row.to_dict()}), 201


@payroll_bp.get("/superadmin/payroll/requests")
@permission_required(Permissions.PAYROLL_VIEW)
def superadmin_list_requests():
    cid = _company_id()
    user_role = getattr(g.user, "role", "EMPLOYEE")
    
    q = PayrollChangeRequest.query.filter_by(company_id=cid)
    if user_role == "HR":
        from models.user import User
        q = q.outerjoin(Employee, PayrollChangeRequest.employee_id == Employee.id).outerjoin(User, Employee.user_id == User.id)
        # HR sees global requests (null employee) OR requests for Manager/Employee
        q = q.filter(or_(PayrollChangeRequest.employee_id == None, User.role.in_(["MANAGER", "EMPLOYEE"])))

    rows = q.order_by(PayrollChangeRequest.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.get("/admin/payroll/requests")
@permission_required(Permissions.PAYROLL_VIEW)
def admin_list_requests():
    cid = _company_id()
    # reuse superadmin logic
    return superadmin_list_requests()


@payroll_bp.post("/superadmin/payroll/requests/<int:req_id>/approve")
@permission_required(Permissions.PAYROLL_CREATE)
def superadmin_approve_request(req_id):
    # Superadmin typically approves paygrade/payrole requests
    cid = _company_id()
    req_row = PayrollChangeRequest.query.filter_by(id=req_id, company_id=cid).first()
    if not req_row:
        return jsonify({"success": False, "message": "Request not found"}), 404
    if req_row.status != "PENDING":
        return jsonify({"success": False, "message": "Request already processed"}), 400

    # apply only for PAY_GRADE / PAY_ROLE
    if req_row.request_type not in ["PAY_GRADE", "PAY_ROLE"]:
        return jsonify({"success": False, "message": "Superadmin approves only PAY_GRADE/PAY_ROLE"}), 400

    _apply_request(req_row)
    req_row.status = "APPROVED"
    req_row.approved_by = getattr(g.user, "id", None)
    req_row.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Approved", "data": req_row.to_dict()}), 200


@payroll_bp.post("/admin/payroll/requests/<int:req_id>/approve")
@permission_required(Permissions.PAYROLL_CREATE)
def admin_approve_request(req_id):
    # Admin typically approves payslip requests
    cid = _company_id()
    req_row = PayrollChangeRequest.query.filter_by(id=req_id, company_id=cid).first()
    if not req_row:
        return jsonify({"success": False, "message": "Request not found"}), 404
    if req_row.status != "PENDING":
        return jsonify({"success": False, "message": "Request already processed"}), 400

    if req_row.request_type != "PAY_SLIP":
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
@permission_required(Permissions.PAYROLL_VIEW)
def list_salary_assignments():
    cid = _company_id()
    user_role = getattr(g.user, "role", "EMPLOYEE")
    
    q = SalaryStructureAssignment.query.filter_by(company_id=cid, status="ACTIVE")
    if user_role == "HR":
        q = q.join(Employee, SalaryStructureAssignment.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
        
    rows = q.order_by(SalaryStructureAssignment.id.desc()).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200


@payroll_bp.post("/superadmin/salary-assignments")
@permission_required(Permissions.PAYROLL_CREATE)
def create_salary_assignment():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    if g.user.role == "SUPER_ADMIN" and not cid:
        cid = data.get("company_id")

    if not cid:
        return jsonify({"success": False, "message": "company_id is required"}), 400

    emp_id = data.get("employee_id")
    grade_id = data.get("pay_grade_id") # Legacy
    struct_id = data.get("salary_structure_id") # New modular
    from_date_str = data.get("from_date")

    if not emp_id or not from_date_str:
        return jsonify({"success": False, "message": "employee_id and from_date are required"}), 400
    
    if not grade_id and not struct_id:
        return jsonify({"success": False, "message": "pay_grade_id or salary_structure_id is required"}), 400

    from_date = parse_date(from_date_str)
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
@permission_required(Permissions.PAYROLL_VIEW)
def list_salary_components():
    cid = _company_id()
    rows = SalaryComponent.query.filter_by(company_id=cid, status="ACTIVE").all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200

@payroll_bp.post("/superadmin/payroll/components")
@permission_required(Permissions.PAYROLL_CREATE)
def create_salary_component():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    if g.user.role == "SUPER_ADMIN" and not cid:
        cid = data.get("company_id")

    if not cid:
        return jsonify({"success": False, "message": "company_id is required"}), 400
    
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
@permission_required(Permissions.PAYROLL_EDIT)
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
@permission_required(Permissions.PAYROLL_VIEW)
def list_salary_structures():
    cid = _company_id()
    rows = SalaryStructure.query.filter_by(company_id=cid, status="ACTIVE").all()
    return jsonify({"success": True, "data": [r.to_dict() for r in rows]}), 200

@payroll_bp.post("/superadmin/payroll/structures")
@permission_required(Permissions.PAYROLL_CREATE)
def create_salary_structure():
    cid = _company_id()
    data = request.get_json(silent=True) or {}

    if g.user.role == "SUPER_ADMIN" and not cid:
        cid = data.get("company_id")

    if not cid:
        return jsonify({"success": False, "message": "company_id is required"}), 400
    
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
@permission_required(Permissions.PAYROLL_VIEW)
def get_statutory_settings():
    cid = _company_id()
    st = StatutorySettings.query.filter_by(company_id=cid).first()
    if not st:
        st = StatutorySettings(company_id=cid)
        db.session.add(st)
        db.session.commit()
    return jsonify({"success": True, "data": st.to_dict()}), 200

@payroll_bp.put("/superadmin/payroll/statutory")
@permission_required(Permissions.PAYROLL_EDIT)
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
@permission_required(Permissions.PAYROLL_VIEW)
def list_employees_dropdown():
    cid = _company_id()
    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = Employee.query.filter_by(company_id=cid)
    
    if user_role == "HR":
        q = q.join(User, Employee.user_id == User.id).filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
        
    rows = q.all()
    data = [{"id": r.id, "name": r.full_name, "employee_id": r.employee_id} for r in rows]
    return jsonify({"success": True, "data": data}), 200


@payroll_bp.get("/superadmin/paygrades-dropdown")
@permission_required(Permissions.PAYROLL_VIEW)
def list_paygrades_dropdown():
    cid = _company_id()
    rows = PayGrade.query.filter_by(company_id=cid, status="ACTIVE").all()
    data = [{"id": r.id, "grade_name": r.grade_name} for r in rows]
    return jsonify({"success": True, "data": data}), 200

@payroll_bp.get("/superadmin/structures-dropdown")
@permission_required(Permissions.PAYROLL_VIEW)
def list_structures_dropdown():
    cid = _company_id()
    rows = SalaryStructure.query.filter_by(company_id=cid, status="ACTIVE").all()
    data = [{"id": r.id, "name": r.name} for r in rows]
    return jsonify({"success": True, "data": data}), 200

@payroll_bp.get("/superadmin/components-dropdown")
@permission_required(Permissions.PAYROLL_VIEW)
def list_components_dropdown():
    cid = _company_id()
    rows = SalaryComponent.query.filter_by(company_id=cid, status="ACTIVE").all()
    data = [{"id": r.id, "name": r.name, "type": r.type} for r in rows]
    return jsonify({"success": True, "data": data}), 200

# =========================================================
# FORM-16 / TAX CERTIFICATES
# =========================================================

@payroll_bp.route("/payroll/form16", methods=["GET"])
@permission_required(Permissions.PAYROLL_VIEW)
def get_form16():
    emp_id = request.args.get("employee_id")
    fy = request.args.get("fy")
    cid = _company_id()
    
    if not emp_id or not fy:
        # If no specific params, return all available for the company (optional)
        records = Form16.query.filter_by(company_id=cid).all()
        return jsonify({"success": True, "data": [r.to_dict() for r in records]}), 200
        
    record = Form16.query.filter_by(employee_id=emp_id, fy=fy, company_id=cid).first()
    if not record:
        return jsonify({"success": False, "message": "Form-16 not found"}), 404
        
    return jsonify({"success": True, "data": record.to_dict()}), 200

@payroll_bp.route("/payroll/form16", methods=["POST"])
@permission_required(Permissions.PAYROLL_CREATE)
def save_form16():
    data = request.get_json(silent=True) or {}
    cid = _company_id()
    
    emp_id = data.get("employee_id")
    fy = data.get("fy")
    
    if not emp_id or not fy:
        return jsonify({"success": False, "message": "employee_id and fy are required"}), 400
        
    record = Form16.query.filter_by(employee_id=emp_id, fy=fy, company_id=cid).first()
    if not record:
        record = Form16(employee_id=emp_id, fy=fy, company_id=cid)
        db.session.add(record)
        
    record.ay = data.get("ay", record.ay or "")
    record.pan = data.get("pan", record.pan or "")
    record.tan = data.get("tan", record.tan or "")
    record.employer_pan = data.get("employer_pan", record.employer_pan or "")
    record.part_a = data.get("partA", record.part_a or {})
    record.part_b = data.get("partB", record.part_b or {})
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
        
    return jsonify({"success": True, "message": "Form-16 saved successfully", "data": record.to_dict()}), 200
    
# =========================================================
# FULL & FINAL SETTLEMENT (F&F)
# =========================================================

@payroll_bp.route("/payroll/fnf", methods=["GET"])
@permission_required(Permissions.PAYROLL_VIEW)
def get_fnf():
    cid = _company_id()
    emp_id = request.args.get("employee_id")
    
    if emp_id:
        record = FullAndFinal.query.filter_by(employee_id=emp_id, company_id=cid).first()
        if not record:
            return jsonify({"success": False, "message": "F&F record not found"}), 404
        return jsonify({"success": True, "data": record.to_dict()}), 200
    
    # Otherwise return all for the company
    records = FullAndFinal.query.filter_by(company_id=cid).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in records]}), 200

@payroll_bp.route("/payroll/fnf", methods=["POST"])
@permission_required(Permissions.PAYROLL_CREATE)
def save_fnf():
    data = request.get_json(silent=True) or {}
    cid = _company_id()
    emp_id = data.get("employee_id")
    
    if not emp_id:
        return jsonify({"success": False, "message": "employee_id is required"}), 400
        
    record = FullAndFinal.query.filter_by(employee_id=emp_id, company_id=cid).first()
    if not record:
        record = FullAndFinal(employee_id=emp_id, company_id=cid)
        db.session.add(record)
        
    # Update fields
    if "resignDate" in data and data["resignDate"]:
        try:
            record.resign_date = datetime.strptime(data["resignDate"], '%d %b %Y').date()
        except:
             record.resign_date = datetime.strptime(data["resignDate"], '%Y-%m-%d').date()
             
    if "lastWorkingDay" in data and data["lastWorkingDay"]:
        try:
            record.last_working_day = datetime.strptime(data["lastWorkingDay"], '%d %b %Y').date()
        except:
            record.last_working_day = datetime.strptime(data["lastWorkingDay"], '%Y-%m-%d').date()
        
    record.notice_period_required = data.get("noticePeriodRequired", record.notice_period_required)
    record.notice_period_served = data.get("noticePeriodServed", record.notice_period_served)
    record.notice_status = data.get("noticeStatus", record.notice_status)
    record.status = data.get("status", record.status)
    record.settlement_data = data.get("settlement", record.settlement_data)
    record.exit_clearance = data.get("clearance", record.exit_clearance)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
        
    return jsonify({"success": True, "message": "F&F record saved successfully", "data": record.to_dict()}), 200
@payroll_bp.get("/payroll/reports/salary-register")
@token_required
@permission_required(Permissions.PAYROLL_VIEW)
def get_salary_register():
    cid = _company_id()
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    if not month or not year:
        now = datetime.utcnow()
        month = month or now.month
        year = year or now.year

    # Fetch all active payslips for the given period and company
    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = PaySlip.query.filter_by(
        company_id=cid, 
        pay_month=month, 
        pay_year=year,
        is_deleted=False
    )
    
    if user_role == "HR":
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
        
    payslips = q.all()

    report_data = []
    for ps in payslips:
        employee = Employee.query.get(ps.employee_id)
        if not employee:
            continue
            
        earnings = ps.earnings_dict
        basic = earnings.get("Basic") or earnings.get("BASIC") or 0.0
        hra = earnings.get("HRA") or earnings.get("House Rent Allowance") or 0.0
        
        # Calculate other allowances (Gross - Basic - HRA)
        # Note: Allowances in the UI seems to be a catch-all for other earnings
        other_allowances = ps.gross_salary - basic - hra
        
        report_data.append({
            "eid": employee.employee_id,
            "name": employee.full_name,
            "dept": employee.department or "N/A",
            "basic": f"₹{basic:,.0f}",
            "hra": f"₹{hra:,.0f}",
            "allow": f"₹{other_allowances:,.0f}",
            "gross": f"₹{ps.gross_salary:,.0f}",
            "ded": f"₹{ps.total_deductions:,.0f}",
            "net": f"₹{ps.net_salary:,.0f}"
        })

    return jsonify({
        "success": True, 
        "data": report_data,
        "count": len(report_data),
        "period": f"{calendar.month_name[month]} {year}"
    }), 200

@payroll_bp.get("/payroll/reports/income-tax")
@permission_required(Permissions.PAYROLL_VIEW)
def get_income_tax_report():
    cid = _company_id()
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if not month or not year:
        now = datetime.utcnow()
        month, year = now.month, now.year

    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = PaySlip.query.filter_by(company_id=cid, pay_month=month, pay_year=year, is_deleted=False)
    if user_role == "HR":
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
    
    payslips = q.all()
    report_data = []
    
    # Financial Year logic (April to March)
    fy_start_year = year if month >= 4 else year - 1
    
    for ps in payslips:
        emp = Employee.query.get(ps.employee_id)
        if not emp: continue
        
        # PAN from Documents
        pan_doc = EmployeeDocument.query.filter_by(employee_id=emp.id, document_type="PAN").first()
        pan = pan_doc.document_number if pan_doc else "N/A"
        
        # TDS YTD
        ytd_q = db.session.query(func.sum(PaySlip.calculated_tds)).filter(
            PaySlip.employee_id == emp.id,
            PaySlip.company_id == cid,
            PaySlip.is_deleted == False
        )
        # Filter for current FY
        ytd_q = ytd_q.filter(
            or_(
                and_(PaySlip.pay_year == fy_start_year, PaySlip.pay_month >= 4),
                and_(PaySlip.pay_year == fy_start_year + 1, PaySlip.pay_month <= 3)
            )
        )
        tds_ytd = ytd_q.scalar() or 0.0
        
        # Calculate Taxable Income (Approx: Gross * 12 or based on structured data if available)
        # For simplicity in this report, we'll show Annual CTC or Gross * 12
        taxable_income = ps.annual_ctc or (ps.gross_salary * 12)

        report_data.append({
            "eid": emp.employee_id,
            "name": emp.full_name,
            "pan": pan,
            "taxable_income": f"₹{taxable_income:,.0f}",
            "tds_month": f"₹{ps.calculated_tds:,.0f}",
            "tds_ytd": f"₹{tds_ytd:,.0f}",
            "regime": ps.tax_regime
        })

    return jsonify({"success": True, "data": report_data, "period": f"{calendar.month_name[month]} {year}"}), 200

@payroll_bp.get("/payroll/reports/professional-tax")
@permission_required(Permissions.PAYROLL_VIEW)
def get_professional_tax_report():
    cid = _company_id()
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if not month or not year:
        now = datetime.utcnow()
        month, year = now.month, now.year

    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = PaySlip.query.filter_by(company_id=cid, pay_month=month, pay_year=year, is_deleted=False)
    if user_role == "HR":
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
    
    payslips = q.all()
    report_data = []
    
    for ps in payslips:
        emp = Employee.query.get(ps.employee_id)
        if not emp: continue
        
        # State from Address
        addr = EmployeeAddress.query.filter_by(employee_id=emp.id, address_type="PRESENT").first()
        state = addr.state if addr else "N/A"
        
        pt_amount = ps.deductions_dict.get("Professional Tax") or ps.deductions_dict.get("PT") or 0.0
        
        # PT Slab logic (Simplified)
        slab = "> ₹15,000" if ps.gross_salary > 15000 else "Exempt"

        report_data.append({
            "eid": emp.employee_id,
            "name": emp.full_name,
            "state": state,
            "gross": f"₹{ps.gross_salary:,.0f}",
            "slab": slab,
            "pt_amount": f"₹{pt_amount:,.0f}",
            "status": "Remitted" if ps.status == "FINAL" else "Pending"
        })

    return jsonify({"success": True, "data": report_data, "period": f"{calendar.month_name[month]} {year}"}), 200

@payroll_bp.get("/payroll/reports/general-ledger")
@permission_required(Permissions.PAYROLL_VIEW)
def get_general_ledger_report():
    cid = _company_id()
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if not month or not year:
        now = datetime.utcnow()
        month, year = now.month, now.year

    # Aggregated Ledger entries for the company
    # General Ledger typically shows totals across the whole company
    # But for HR, we should only show totals for their accessible roles?
    # Usually GL is an Admin/Account role thing. But if HR accesses it, we filter.
    
    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = PaySlip.query.filter_by(company_id=cid, pay_month=month, pay_year=year, is_deleted=False)
    if user_role == "HR":
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
    
    payslips = q.all()
    
    total_basic = 0.0
    total_hra = 0.0
    total_pf = 0.0
    total_tds = 0.0
    total_net = 0.0
    
    for ps in payslips:
        total_basic += ps.earnings_dict.get("Basic", 0.0)
        total_hra += ps.earnings_dict.get("HRA", 0.0)
        total_pf += ps.deductions_dict.get("PF", 0.0) + ps.deductions_dict.get("Provident Fund", 0.0)
        total_tds += ps.calculated_tds
        total_net += ps.net_salary

    report_date = datetime(year, month, 1).strftime("%d %b %Y")
    data = [
        {"date": report_date, "account": "Salary Payable", "desc": f"Basic Salary - {calendar.month_name[month]}", "debit": f"{total_basic:,.0f}", "credit": "-", "balance": f"{total_basic:,.0f}"},
        {"date": report_date, "account": "HRA Payable", "desc": f"HRA Payout - {calendar.month_name[month]}", "debit": f"{total_hra:,.0f}", "credit": "-", "balance": f"{total_hra + total_basic:,.0f}"},
        {"date": report_date, "account": "PF Payable", "desc": f"Employee PF - {calendar.month_name[month]}", "debit": "-", "credit": f"{total_pf:,.0f}", "balance": f"{total_hra + total_basic - total_pf:,.0f}"},
        {"date": report_date, "account": "TDS Payable", "desc": f"TDS Deducted - {calendar.month_name[month]}", "debit": "-", "credit": f"{total_tds:,.0f}", "balance": f"{total_hra + total_basic - total_pf - total_tds:,.0f}"},
        {"date": report_date, "account": "Bank Account", "desc": "Salary Disbursed", "debit": "-", "credit": f"{total_net:,.0f}", "balance": "0.00"}
    ]

    return jsonify({"success": True, "data": data, "period": f"{calendar.month_name[month]} {year}"}), 200

@payroll_bp.get("/payroll/reports/accounts-payable")
@permission_required(Permissions.PAYROLL_VIEW)
def get_accounts_payable_report():
    cid = _company_id()
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if not month or not year:
        now = datetime.utcnow()
        month, year = now.month, now.year

    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = PaySlip.query.filter_by(company_id=cid, pay_month=month, pay_year=year, is_deleted=False)
    if user_role == "HR":
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
    
    payslips = q.all()
    
    total_salary = 0.0
    total_pf = 0.0
    total_pt = 0.0
    total_tds = 0.0
    
    for ps in payslips:
        if ps.status != "FINAL": # Only pending if not finalized? Or maybe just sum everything for current month.
            # In the screenshot, it shows "Outstanding liabilities".
            total_salary += ps.net_salary
            total_pf += ps.deductions_dict.get("PF", 0.0) + ps.deductions_dict.get("Provident Fund", 0.0)
            total_pt += ps.deductions_dict.get("Professional Tax", 0.0) + ps.deductions_dict.get("PT", 0.0)
            total_tds += ps.calculated_tds

    data = [
        {"liability": "Unpaid Salaries", "amount": f"₹{total_salary:,.0f}", "due_date": f"05 {calendar.month_name[(month % 12) + 1]} {year if month < 12 else year+1}", "status": "Pending"},
        {"liability": "PF Contributions", "amount": f"₹{total_pf:,.0f}", "due_date": "15th of next month", "status": "Accrued"},
        {"liability": "Professional Tax", "amount": f"₹{total_pt:,.0f}", "due_date": "State specific", "status": "Accrued"},
        {"liability": "TDS Payable", "amount": f"₹{total_tds:,.0f}", "due_date": "07th of next month", "status": "Accrued"}
    ]

    return jsonify({"success": True, "data": data, "period": f"{calendar.month_name[month]} {year}"}), 200

@payroll_bp.get("/admin/payroll/dashboard")
@permission_required(Permissions.PAYROLL_VIEW)
def get_payroll_dashboard():
    cid = _company_id()
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    if not month or not year:
        now = datetime.utcnow()
        month = month or now.month
        year = year or now.year

    # Aggregate Data
    user_role = getattr(g.user, "role", "EMPLOYEE")
    q = PaySlip.query.filter_by(
        company_id=cid, 
        pay_month=month, 
        pay_year=year,
        is_deleted=False
    )
    if user_role == "HR":
        q = q.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        q = q.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
    payslips = q.all()

    total_payout = sum(ps.net_salary for ps in payslips)
    processed_count = sum(1 for ps in payslips if ps.status == "FINAL")
    draft_count = sum(1 for ps in payslips if ps.status == "DRAFT")
    avg_salary = total_payout / len(payslips) if payslips else 0

    # Calculate MoM Growth
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    pq = PaySlip.query.filter_by(
        company_id=cid, 
        pay_month=prev_month, 
        pay_year=prev_year,
        is_deleted=False
    )
    if user_role == "HR":
        pq = pq.join(Employee, PaySlip.employee_id == Employee.id).join(User, Employee.user_id == User.id)
        pq = pq.filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
    prev_payslips = pq.all()
    prev_payout = sum(ps.net_salary for ps in prev_payslips)
    
    growth_pct = 0
    if prev_payout > 0:
        growth_pct = ((total_payout - prev_payout) / prev_payout) * 100
    growth_str = f"{'+' if growth_pct >= 0 else ''}{growth_pct:.1f}%"

    # Component Analysis
    earnings_breakdown = {}
    deductions_breakdown = {}
    for ps in payslips:
        for e in ps.earnings:
            earnings_breakdown[e.component] = earnings_breakdown.get(e.component, 0) + e.amount
        for d in ps.deductions:
            deductions_breakdown[d.component] = deductions_breakdown.get(d.component, 0) + d.amount

    # Dept-wise Distribution
    dept_distribution = {}
    for ps in payslips:
        employee = Employee.query.get(ps.employee_id)
        dept = employee.department if employee else "Unknown"
        dept_distribution[dept] = dept_distribution.get(dept, 0) + ps.net_salary

    # Recent Runs
    recent_runs = []
    # Fetch last 4 months
    for i in range(4):
        d = datetime(year, month, 1) - timedelta(days=i*30)
        m, y = d.month, d.year
        month_slips = PaySlip.query.filter_by(company_id=cid, pay_month=m, pay_year=y, is_deleted=False).all()
        recent_runs.append({
            "id": f"PAY-{y}{m:02d}",
            "period": f"{calendar.month_name[m]} {y}",
            "employees": len(month_slips),
            "payout": sum(ps.net_salary for ps in month_slips),
            "status": "Completed" if any(ps.status == "FINAL" for ps in month_slips) else "Pending"
        })

    # Statutory Status
    stat_settings = StatutorySettings.query.filter_by(company_id=cid).first()
    compliance = [
        {"name": "Provident Fund (PF)", "status": "On Track" if stat_settings and stat_settings.enable_pf else "Not Configured"},
        {"name": "ESIC Contribution", "status": "On Track" if stat_settings and stat_settings.enable_esi else "Not Configured"},
        {"name": "Professional Tax", "status": "On Track"},
        {"name": "TDS Remittance", "status": "Action Required" if draft_count > 0 else "On Track"}
    ]

    return jsonify({
        "success": True,
        "data": {
            "summary": {
                "totalPayout": total_payout,
                "processed": processed_count,
                "pending": draft_count,
                "avgSalary": round(avg_salary, 2),
                "growth": growth_str
            },
            "componentAnalysis": {
                "earnings": [{"name": k, "value": v} for k, v in earnings_breakdown.items()],
                "deductions": [{"name": k, "value": v} for k, v in deductions_breakdown.items()]
            },
            "deptDistribution": [{"name": k, "value": v} for k, v in dept_distribution.items()],
            "recentRuns": recent_runs,
            "compliance": compliance
        }
    }), 200

# =========================================================
# PAYROLL LETTERS (Increment, Promotion, etc.)
# =========================================================

@payroll_bp.get("/payroll/employees")
@token_required
@permission_required(Permissions.PAYROLL_VIEW)
def list_payroll_employees():
    cid = _company_id()
    if not cid:
        return jsonify({"success": False, "message": "Company ID not found"}), 400
    
    user_role = getattr(g.user, "role", "EMPLOYEE")
    # Get all employees for the company
    q = Employee.query.filter_by(company_id=cid)
    if user_role == "HR":
        q = q.join(User, Employee.user_id == User.id).filter(User.role.in_(["MANAGER", "EMPLOYEE"]))
        
    employees = q.all()
    
    return jsonify({
        "success": True, 
        "data": [{
            "id": e.id,
            "employee_id": e.employee_id,
            "name": e.full_name,
            "department": e.department,
            "designation": e.designation,
            "current_salary": e.ctc
        } for e in employees]
    }), 200

@payroll_bp.post("/payroll/letters")
@permission_required(Permissions.PAYROLL_CREATE)
def create_payroll_letter():
    cid = _company_id()
    data = request.get_json(silent=True) or {}
    
    required = ["employee_id", "letter_type", "effective_date", "content_data"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "message": f"{field} is required"}), 400
            
    letter = PayrollLetter(
        employee_id=data["employee_id"],
        company_id=cid,
        letter_type=data["letter_type"],
        effective_date=datetime.strptime(data["effective_date"], "%Y-%m-%d").date(),
        content_data=data["content_data"],
        status=data.get("status", "ISSUED")
    )
    
    db.session.add(letter)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
        
    return jsonify({"success": True, "data": letter.to_dict()}), 201

@payroll_bp.get("/payroll/letters")
@permission_required(Permissions.PAYROLL_VIEW)
def list_payroll_letters():
    cid = _company_id()
    letters = PayrollLetter.query.filter_by(company_id=cid).order_by(PayrollLetter.created_at.desc()).all()
    return jsonify({"success": True, "data": [l.to_dict() for l in letters]}), 200
