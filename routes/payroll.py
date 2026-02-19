import io
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, g
from models import db
from utils.decorators import token_required
from models.payroll import PayGrade, PayRole, PaySlip, PayrollChangeRequest

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


def _sum_values(d):
    if not d:
        return 0.0
    total = 0.0
    for _, v in d.items():
        try:
            total += float(v)
        except Exception:
            pass
    return round(total, 2)


def _recalc_payslip(ps: PaySlip):
    ps.total_earnings = _sum_values(ps.earnings)
    ps.total_deductions = _sum_values(ps.deductions)
    ps.total_reimbursements = _sum_values(ps.reimbursements)

    ps.gross_salary = ps.total_earnings
    ps.net_salary = round(ps.total_earnings - ps.total_deductions + ps.total_reimbursements, 2)

    ps.monthly_ctc = round(ps.gross_salary, 2)
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
        c.drawString(300, y, f"{r.basic_percent:.2f}")
        c.drawString(360, y, f"{r.hra_percent:.2f}")
        c.drawString(420, y, f"{r.ta_percent:.2f}")
        c.drawString(470, y, f"{r.medical_percent:.2f}")
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

    for f in ["min_salary", "max_salary", "basic_percent", "hra_percent", "ta_percent", "medical_percent"]:
        if f in data:
            setattr(row, f, float(data[f] or 0))

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
    data = request.get_json(silent=True) or {}

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
        earnings=data.get("earnings") or {},
        deductions=data.get("deductions") or {},
        employer_contribution=data.get("employer_contribution") or {},
        reimbursements=data.get("reimbursements") or {},
        bank_account_number=data.get("bank_account_number"),
        uan_number=data.get("uan_number"),
        esi_account_number=data.get("esi_account_number"),
        tax_regime=data.get("tax_regime", "Old Regime"),
        section_80c=float(data.get("section_80c", 0) or 0),
        monthly_rent=float(data.get("monthly_rent", 0) or 0),
        city_type=data.get("city_type", "Non-Metro"),
        other_deductions=float(data.get("other_deductions", 0) or 0),
        calculated_tds=float(data.get("calculated_tds", 0) or 0),
        pf_employee_percent=float(data.get("pf_employee_percent", 12) or 12),
        pf_employer_percent=float(data.get("pf_employer_percent", 12) or 12),
        esi_employee_percent=float(data.get("esi_employee_percent", 0.75) or 0.75),
        esi_employer_percent=float(data.get("esi_employer_percent", 3.25) or 3.25),
        created_by=getattr(g.user, "id", None),
    )

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

    data = request.get_json(silent=True) or {}

    # simple fields
    for f in ["department_id", "pay_role_id", "total_days", "paid_days", "lwp_days"]:
        if f in data:
            setattr(ps, f, int(data[f] or 0) if f in ["total_days", "paid_days", "lwp_days"] else data[f])

    if "pay_date" in data:
        pd = _parse_date(data["pay_date"])
        if data["pay_date"] and not pd:
            return jsonify({"success": False, "message": "pay_date must be YYYY-MM-DD"}), 400
        ps.pay_date = pd

    # json blocks
    for f in ["earnings", "deductions", "employer_contribution", "reimbursements"]:
        if f in data and isinstance(data[f], dict):
            setattr(ps, f, data[f])

    # optional blocks
    for f in ["bank_account_number", "uan_number", "esi_account_number", "tax_regime", "city_type"]:
        if f in data:
            setattr(ps, f, data[f])

    for f in [
        "section_80c", "monthly_rent", "other_deductions", "calculated_tds",
        "pf_employee_percent", "pf_employer_percent", "esi_employee_percent", "esi_employer_percent"
    ]:
        if f in data:
            setattr(ps, f, float(data[f] or 0))

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
        nonlocal y
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, title)
        y -= 14
        c.setFont("Helvetica", 10)

        if not data_dict:
            c.drawString(60, y, "-")
            y -= 14
            return

        for k, v in data_dict.items():
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(60, y, str(k))
            try:
                c.drawRightString(520, y, f"{float(v or 0):.2f}")
            except Exception:
                c.drawRightString(520, y, "0.00")
            y -= 12
        y -= 10

    section("Earnings", ps.earnings or {})
    section("Deductions", ps.deductions or {})
    section("Employer Contribution", ps.employer_contribution or {})
    section("Reimbursements", ps.reimbursements or {})

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