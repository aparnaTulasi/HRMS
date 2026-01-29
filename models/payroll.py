from datetime import datetime
from models import db
from sqlalchemy import CheckConstraint

class SalaryComponent(db.Model):
    __tablename__ = 'salary_components'
    id = db.Column(db.Integer, primary_key=True) # component_id
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    component_name = db.Column(db.String(100), nullable=False)
    component_code = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(20), nullable=False) # Earning/Deduction
    calculation_type = db.Column(db.String(20), nullable=False) # Fixed/Percentage
    percentage_value = db.Column(db.Float(5,2))
    taxable = db.Column(db.String(5), default='Yes', nullable=False) # Yes/No
    order_no = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.String(5), default='Yes', nullable=False) # Yes/No

    __table_args__ = (
        db.UniqueConstraint('component_name', 'company_id', name='uq_component_name_company'),
        db.UniqueConstraint('component_code', 'company_id', name='uq_component_code_company'),
        CheckConstraint("type IN ('Earning', 'Deduction')", name='chk_comp_type'),
        CheckConstraint("calculation_type IN ('Fixed', 'Percentage')", name='chk_calc_type'),
        CheckConstraint("taxable IN ('Yes', 'No')", name='chk_taxable'),
        CheckConstraint("is_active IN ('Yes', 'No')", name='chk_active_comp'),
    )

class SalaryStructure(db.Model):
    __tablename__ = 'salary_structures'
    id = db.Column(db.Integer, primary_key=True) # structure_id
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    structure_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    base_salary = db.Column(db.Float(10,2))
    is_active = db.Column(db.String(5), default='Yes', nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('structure_name', 'company_id', name='uq_structure_name_company'),
        CheckConstraint("is_active IN ('Yes', 'No')", name='chk_active_struct'),
    )
    
    components = db.relationship('SalaryStructureComponent', backref='structure', lazy=True)

class SalaryStructureComponent(db.Model):
    __tablename__ = 'salary_structure_components'
    id = db.Column(db.Integer, primary_key=True)
    structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('salary_components.id'), nullable=False)
    
    percentage = db.Column(db.Float(5,2))
    fixed_amount = db.Column(db.Float(10,2))
    depends_on_component_id = db.Column(db.Integer, db.ForeignKey('salary_components.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('structure_id', 'component_id', name='uq_ssc'),
    )
    
    component = db.relationship('SalaryComponent', foreign_keys=[component_id])
    depends_on = db.relationship('SalaryComponent', foreign_keys=[depends_on_component_id])

class EmployeeSalaryStructure(db.Model):
    __tablename__ = 'employee_salary_structure'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id'), nullable=False)
    
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'effective_from', name='uq_ess'),
    )

class PayrollRun(db.Model):
    __tablename__ = 'payroll_run'
    id = db.Column(db.Integer, primary_key=True) # payroll_id
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)
    run_date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), default='In Progress', nullable=False) # In Progress, Completed, Locked
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    remarks = db.Column(db.String(300))

    __table_args__ = (
        db.UniqueConstraint('month_year', 'company_id', name='uq_pr_month_company'),
        CheckConstraint("status IN ('In Progress', 'Completed', 'Locked')", name='chk_payroll_status'),
    )

class PayrollRunEmployee(db.Model):
    __tablename__ = 'payroll_run_employees'
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    paid_days = db.Column(db.Float(5,2))
    lop_days = db.Column(db.Float(5,2))
    overtime_hours = db.Column(db.Float(5,2))
    overtime_amount = db.Column(db.Float(10,2))

    __table_args__ = (
        db.UniqueConstraint('payroll_id', 'employee_id', name='uq_pre'),
    )

class PayrollEarning(db.Model):
    __tablename__ = 'payroll_earnings'
    id = db.Column(db.Integer, primary_key=True) # earning_id
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('salary_components.id'), nullable=False)
    amount = db.Column(db.Float(10,2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('payroll_id', 'employee_id', 'component_id', name='uq_pe'),
    )

class PayrollDeduction(db.Model):
    __tablename__ = 'payroll_deductions'
    id = db.Column(db.Integer, primary_key=True) # deduction_id
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('salary_components.id'), nullable=False)
    amount = db.Column(db.Float(10,2), nullable=False)
    is_manual = db.Column(db.String(5), default='No') # Yes/No

    __table_args__ = (
        db.UniqueConstraint('payroll_id', 'employee_id', 'component_id', name='uq_pd'),
        CheckConstraint("is_manual IN ('Yes', 'No')", name='chk_is_manual'),
    )

class PayrollSummary(db.Model):
    __tablename__ = 'payroll_summary'
    id = db.Column(db.Integer, primary_key=True) # summary_id
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    gross_salary = db.Column(db.Float(12,2))
    total_deductions = db.Column(db.Float(12,2))
    net_salary = db.Column(db.Float(12,2))
    employer_contribution = db.Column(db.Float(12,2))

    __table_args__ = (
        db.UniqueConstraint('payroll_id', 'employee_id', name='uq_ps'),
    )