from datetime import datetime
<<<<<<< HEAD
from typing import Dict, Any, cast, Optional
from models import db # pyre-ignore[21]

# =========================================================
# NEW MODULAR PAYROLL MODELS
# =========================================================

class SalaryComponent(db.Model):
    __tablename__ = "salary_components"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    # EARNING, DEDUCTION, STATUTORY_DEDUCTION, EMPLOYER_CONTRIBUTION, REIMBURSEMENT
    type = db.Column(db.String(50), nullable=False)
    # FLAT, PERCENT_OF_BASIC, PERCENT_OF_GROSS, PERCENT_OF_CTC
    calculation_type = db.Column(db.String(50), nullable=False, default="FLAT")
    amount_value = db.Column(db.Float, default=0.0)
    
    is_taxable = db.Column(db.Boolean, default=True)
    is_statutory = db.Column(db.Boolean, default=False)
    is_part_of_ctc = db.Column(db.Boolean, default=True)
    # MONTHLY, YEARLY
    frequency = db.Column(db.String(20), default="MONTHLY")
    
    status = db.Column(db.String(20), default="ACTIVE")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "calculation_type": self.calculation_type,
            "amount_value": self.amount_value,
            "is_taxable": self.is_taxable,
            "is_statutory": self.is_statutory,
            "is_part_of_ctc": self.is_part_of_ctc,
            "frequency": self.frequency,
            "status": self.status
        }

class SalaryStructure(db.Model):
    __tablename__ = "salary_structures"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="ACTIVE")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    components = db.relationship("StructureComponent", backref="structure", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "components": [c.to_dict() for c in self.components],
            "status": self.status
        }

class StructureComponent(db.Model):
    __tablename__ = "structure_components"
    id = db.Column(db.Integer, primary_key=True)
    structure_id = db.Column(db.Integer, db.ForeignKey("salary_structures.id"), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey("salary_components.id"), nullable=False)
    
    # Optional override for the base component value
    override_value = db.Column(db.Float, nullable=True)
    
    component = db.relationship("SalaryComponent")

    def to_dict(self):
        comp_dict = self.component.to_dict() if self.component else {}
        d = dict(comp_dict)
        if self.override_value is not None:
            d["amount_value"] = self.override_value
        d["structure_component_id"] = self.id
        return d

class StatutorySettings(db.Model):
    __tablename__ = "statutory_settings"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True, unique=True)
    
    pf_employee_pct = db.Column(db.Float, default=12.0)
    pf_employer_pct = db.Column(db.Float, default=12.0)
    esi_employee_pct = db.Column(db.Float, default=0.75)
    esi_employer_pct = db.Column(db.Float, default=3.25)
    
    enable_pf = db.Column(db.Boolean, default=True)
    enable_esi = db.Column(db.Boolean, default=True)
    enable_tds = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            "pf_employee_pct": self.pf_employee_pct,
            "pf_employer_pct": self.pf_employer_pct,
            "esi_employee_pct": self.esi_employee_pct,
            "esi_employer_pct": self.esi_employer_pct,
            "enable_pf": self.enable_pf,
            "enable_esi": self.enable_esi,
            "enable_tds": self.enable_tds
        }

# =========================================================
# OLD MODELS (RETAINED FOR COMPATIBILITY / MIGRATION)
# =========================================================
=======
from models import db
>>>>>>> 04003eaf0043fea586f7748da275677b8b3436c1

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

<<<<<<< HEAD
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "grade_name": self.grade_name,
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
            "basic_percent": self.basic_pct,
            "hra_percent": self.hra_pct,
            "ta_percent": self.ta_pct,
            "medical_percent": self.medical_pct,
            "is_active": self.is_active,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

=======
>>>>>>> 04003eaf0043fea586f7748da275677b8b3436c1

class PayRole(db.Model):
    __tablename__ = "pay_roles"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)  # designation/role name
    pay_grade_id = db.Column(db.Integer, db.ForeignKey("pay_grades.id"), nullable=True)

    is_active = db.Column(db.Boolean, default=True)
<<<<<<< HEAD
    status = db.Column(db.String(20), default="ACTIVE")
=======
>>>>>>> 04003eaf0043fea586f7748da275677b8b3436c1

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pay_grade = db.relationship("PayGrade")

<<<<<<< HEAD
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "pay_grade_id": self.pay_grade_id,
            "is_active": self.is_active,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SalaryStructureAssignment(db.Model):
    __tablename__ = "salary_structure_assignments"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    
    # OLD: linked to PayGrade
    pay_grade_id = db.Column(db.Integer, db.ForeignKey("pay_grades.id"), nullable=True)
    # NEW: linked to SalaryStructure
    salary_structure_id = db.Column(db.Integer, db.ForeignKey("salary_structures.id"), nullable=True)
    
    from_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default="ACTIVE")

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", backref="salary_assignments")
    pay_grade = db.relationship("PayGrade")
    salary_structure = db.relationship("SalaryStructure")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "pay_grade_id": self.pay_grade_id,
            "salary_structure_id": self.salary_structure_id,
            "from_date": self.from_date.isoformat() if self.from_date else None,
            "is_active": self.is_active,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.employee_id if self.employee else None,
            "department": self.employee.department if self.employee else None,
            "designation": self.employee.designation if self.employee else None,
            "salary_structure_name": self.salary_structure.name if self.salary_structure else (self.pay_grade.grade_name if self.pay_grade else None)
        }

=======
>>>>>>> 04003eaf0043fea586f7748da275677b8b3436c1

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

<<<<<<< HEAD
    pf_employee_pct = db.Column(db.Float, default=12)
    pf_employer_pct = db.Column(db.Float, default=12)
    esi_employee_pct = db.Column(db.Float, default=0.75)
    esi_employer_pct = db.Column(db.Float, default=3.25)

=======
>>>>>>> 04003eaf0043fea586f7748da275677b8b3436c1
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

<<<<<<< HEAD
    @property
    def earnings_dict(self):
        return {e.component: e.amount for e in self.earnings}

    @property
    def deductions_dict(self):
        return {d.component: d.amount for d in self.deductions}

    @property
    def employer_contrib_dict(self):
        return {c.component: c.amount for c in self.employer_contribs}

    @property
    def reimbursements_dict(self):
        return {r.component: r.amount for r in self.reimbursements}

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "pay_month": self.pay_month,
            "pay_year": self.pay_year,
            "pay_date": self.pay_date.isoformat() if self.pay_date else None,
            "gross_salary": self.gross_salary,
            "net_salary": self.net_salary,
            "status": self.status,
            "annual_ctc": self.annual_ctc,
            "monthly_ctc": self.monthly_ctc,
            "bank_account_no": self.bank_account_no,
            "uan_no": self.uan_no,
            "esi_account_no": self.esi_account_no,
            "tax_regime": self.tax_regime,
            "city_type": self.city_type,
            "pf_employee_percent": self.pf_employee_pct,
            "pf_employer_percent": self.pf_employer_pct,
            "esi_employee_percent": self.esi_employee_pct,
            "esi_employer_percent": self.esi_employer_pct,
            "section_80c": self.section_80c,
            "monthly_rent": self.monthly_rent,
            "other_deductions": self.other_deductions,
            "calculated_tds": self.calculated_tds,
            "earnings": self.earnings_dict,
            "deductions": self.deductions_dict,
            "employer_contribution": self.employer_contrib_dict,
            "reimbursements": self.reimbursements_dict,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

=======
>>>>>>> 04003eaf0043fea586f7748da275677b8b3436c1

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