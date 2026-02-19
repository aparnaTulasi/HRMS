from datetime import datetime
from models import db

class PayGrade(db.Model):
    __tablename__ = "pay_grades"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    grade_name = db.Column(db.String(100), nullable=False)
    min_salary = db.Column(db.Float, nullable=True)
    max_salary = db.Column(db.Float, nullable=True)

    basic_pct = db.Column(db.Float, default=0)
    hra_pct = db.Column(db.Float, default=0)
    ta_pct = db.Column(db.Float, default=0)
    medical_pct = db.Column(db.Float, default=0)

    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")  # ACTIVE/DELETED

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PayRole(db.Model):
    __tablename__ = "pay_roles"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)  # designation/role name
    pay_grade_id = db.Column(db.Integer, db.ForeignKey("pay_grades.id"), nullable=True)

    is_active = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pay_grade = db.relationship("PayGrade")


class PaySlip(db.Model):
    __tablename__ = "payslips"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)

    pay_month = db.Column(db.Integer, nullable=False)
    pay_year = db.Column(db.Integer, nullable=False)
    pay_date = db.Column(db.Date, nullable=True)

    total_days = db.Column(db.Integer, default=0)
    paid_days = db.Column(db.Integer, default=0)
    lwp_days = db.Column(db.Integer, default=0)

    gross_salary = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    total_reimbursements = db.Column(db.Float, default=0)
    net_salary = db.Column(db.Float, default=0)

    annual_ctc = db.Column(db.Float, default=0)
    monthly_ctc = db.Column(db.Float, default=0)

    tax_regime = db.Column(db.String(30), default="OLD")  # OLD/NEW
    section_80c = db.Column(db.Float, default=0)
    monthly_rent = db.Column(db.Float, default=0)
    city_type = db.Column(db.String(30), default="NON_METRO")  # METRO/NON_METRO
    other_deductions = db.Column(db.Float, default=0)
    calculated_tds = db.Column(db.Float, default=0)

    bank_account_no = db.Column(db.String(50), nullable=True)
    uan_no = db.Column(db.String(50), nullable=True)
    esi_account_no = db.Column(db.String(50), nullable=True)

    status = db.Column(db.String(20), default="DRAFT")  # DRAFT/FINAL
    pdf_path = db.Column(db.String(255), nullable=True)

    is_deleted = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    earnings = db.relationship("PayslipEarning", backref="payslip", cascade="all, delete-orphan")
    deductions = db.relationship("PayslipDeduction", backref="payslip", cascade="all, delete-orphan")
    employer_contribs = db.relationship("PayslipEmployerContribution", backref="payslip", cascade="all, delete-orphan")
    reimbursements = db.relationship("PayslipReimbursement", backref="payslip", cascade="all, delete-orphan")


class PayslipEarning(db.Model):
    __tablename__ = "payslip_earnings"
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey("payslips.id"), nullable=False, index=True)
    component = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, default=0)


class PayslipDeduction(db.Model):
    __tablename__ = "payslip_deductions"
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey("payslips.id"), nullable=False, index=True)
    component = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, default=0)


class PayslipEmployerContribution(db.Model):
    __tablename__ = "payslip_employer_contributions"
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey("payslips.id"), nullable=False, index=True)
    component = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, default=0)


class PayslipReimbursement(db.Model):
    __tablename__ = "payslip_reimbursements"
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey("payslips.id"), nullable=False, index=True)
    component = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, default=0)


class PayrollChangeRequest(db.Model):
    __tablename__ = "payroll_change_requests"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    request_type = db.Column(db.String(50), nullable=False)  # e.g., 'SALARY_REVISION', 'BONUS'
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    
    payload = db.Column(db.JSON, nullable=True)  # Store details like { "old_ctc": ..., "new_ctc": ... }
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="PENDING")  # PENDING, APPROVED, REJECTED

    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)