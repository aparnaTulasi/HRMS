from datetime import datetime, date
from models import db

# -----------------------------
# LEGACY TABLES (already existed)
# -----------------------------
class LeaveType(db.Model):
    __tablename__ = 'leave_types'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=True)

    code = db.Column(db.String(20), nullable=False)   # ✅ NEW
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(10), default='DAY')
    allow_half_day = db.Column(db.Boolean, default=False)
    is_paid = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)

    __table_args__ = (db.UniqueConstraint('company_id', 'code', name='uq_leave_type_company_code'),)


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')  # Pending/Pending Approval/Approved/Rejected/Cancelled
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employee = db.relationship('Employee', foreign_keys=[employee_id])

class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='leave_balances')
    leave_type = db.relationship('LeaveType', backref='balances')

# -----------------------------
# NEW TABLES (testing & fixes)
# -----------------------------
class LeavePolicy(db.Model):
    __tablename__ = "leave_policies"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    effective_from = db.Column(db.Date, nullable=False, default=date.today)
    effective_to = db.Column(db.Date, nullable=True)
    config_json = db.Column(db.Text)  # workflow_roles, sandwich, proration, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LeavePolicyMapping(db.Model):
    __tablename__ = "leave_policy_mappings"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    policy_id = db.Column(db.Integer, db.ForeignKey("leave_policies.id"), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey("leave_types.id"), nullable=False)

    # scope (NULL means applies broadly)
    department = db.Column(db.String(120))
    designation = db.Column(db.String(120))
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"))

    # allocation & limits
    annual_allocation = db.Column(db.Float, default=0.0)
    max_balance = db.Column(db.Float)
    carry_forward_limit = db.Column(db.Float)
    encashment_limit = db.Column(db.Float)

    # unit for WFH/hourly leaves
    unit = db.Column(db.String(10), default="DAY")  # DAY/HOUR
    allow_half_day = db.Column(db.Boolean, default=False)
    max_hours_per_day = db.Column(db.Float)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HolidayCalendar(db.Model):
    __tablename__ = "holiday_calendars"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    weekend_days_json = db.Column(db.Text)  # e.g. [5,6] for Sat/Sun (python weekday)
    timezone = db.Column(db.String(64), default="Asia/Kolkata")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Holiday(db.Model):
    __tablename__ = "holidays"
    id = db.Column(db.Integer, primary_key=True)
    calendar_id = db.Column(db.Integer, db.ForeignKey("holiday_calendars.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    is_optional = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("calendar_id", "date", name="uq_calendar_date"),)

class EmployeeHolidayCalendar(db.Model):
    __tablename__ = "employee_holiday_calendars"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    calendar_id = db.Column(db.Integer, db.ForeignKey("holiday_calendars.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("employee_id", "calendar_id", name="uq_emp_calendar"),)

class LeaveRequestDetail(db.Model):
    __tablename__ = "leave_request_details"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("leave_requests.id"), nullable=False, unique=True)

    unit_type = db.Column(db.String(10), default="DAY")  # DAY/HOUR
    units = db.Column(db.Float, default=0.0)
    from_time = db.Column(db.String(10))  # HH:MM
    to_time = db.Column(db.String(10))    # HH:MM
    hours = db.Column(db.Float)
    sandwich_counted = db.Column(db.Boolean, default=False)
    meta_json = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LeaveApprovalStep(db.Model):
    __tablename__ = "leave_approval_steps"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("leave_requests.id"), nullable=False)

    step_no = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    approver_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(20), default="PENDING")  # PENDING/APPROVED/REJECTED/SKIPPED
    comment = db.Column(db.Text)
    acted_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("request_id", "step_no", name="uq_request_step"),)

class LeaveLedger(db.Model):
    __tablename__ = "leave_ledger"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey("leave_types.id"), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey("leave_requests.id"))

    txn_type = db.Column(db.String(20), nullable=False)  # ACCRUAL/DEBIT/CREDIT/ENCASH
    units = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LeaveEncashment(db.Model):
    __tablename__ = "leave_encashments"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey("leave_types.id"), nullable=False)

    units = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
