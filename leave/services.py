import json
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import func, case

from models import db
from models.employee import Employee
from leave.models import (
    LeavePolicy, LeavePolicyMapping,
    HolidayCalendar, Holiday, EmployeeHolidayCalendar,
    LeaveRequestDetail, LeaveApprovalStep, LeaveLedger, LeaveEncashment
)

def json_load(s: Optional[str], default):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default

def daterange(d1: date, d2: date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

def get_employee(emp_user_id: int) -> Optional[Employee]:
    return Employee.query.filter_by(user_id=emp_user_id).first()

def get_employee_calendar(company_id: int, employee_id: int) -> Optional[HolidayCalendar]:
    link = EmployeeHolidayCalendar.query.filter_by(company_id=company_id, employee_id=employee_id).first()
    if link:
        return HolidayCalendar.query.filter_by(id=link.calendar_id, company_id=company_id).first()
    return HolidayCalendar.query.filter_by(company_id=company_id, is_active=True).order_by(HolidayCalendar.id.asc()).first()

def get_holidays_set(company_id: int, calendar_id: int, from_date: date, to_date: date) -> set:
    rows = Holiday.query.filter(
        Holiday.company_id == company_id,
        Holiday.calendar_id == calendar_id,
        Holiday.date >= from_date,
        Holiday.date <= to_date
    ).all()
    return {r.date for r in rows}

def select_policy_mapping(company_id: int, emp: Employee, leave_type_id: int) -> Optional[LeavePolicyMapping]:
    q = LeavePolicyMapping.query.filter_by(company_id=company_id, leave_type_id=leave_type_id, is_active=True)

    # employee-specific
    m = q.filter(LeavePolicyMapping.employee_id == emp.id).order_by(LeavePolicyMapping.id.desc()).first()
    if m:
        return m

    # dept + designation
    if getattr(emp, "department", None) and getattr(emp, "designation", None):
        m = q.filter(
            LeavePolicyMapping.department == emp.department,
            LeavePolicyMapping.designation == emp.designation,
            LeavePolicyMapping.employee_id.is_(None)
        ).order_by(LeavePolicyMapping.id.desc()).first()
        if m:
            return m

    # dept only
    if getattr(emp, "department", None):
        m = q.filter(
            LeavePolicyMapping.department == emp.department,
            LeavePolicyMapping.designation.is_(None),
            LeavePolicyMapping.employee_id.is_(None)
        ).order_by(LeavePolicyMapping.id.desc()).first()
        if m:
            return m

    # default
    return q.filter(
        LeavePolicyMapping.department.is_(None),
        LeavePolicyMapping.designation.is_(None),
        LeavePolicyMapping.employee_id.is_(None)
    ).order_by(LeavePolicyMapping.id.desc()).first()

def get_policy_config(company_id: int, policy_id: int) -> Dict[str, Any]:
    pol = LeavePolicy.query.filter_by(id=policy_id, company_id=company_id, is_active=True).first()
    if not pol:
        return {}
    return json_load(pol.config_json, {})

def compute_units(company_id: int, emp: Employee, mapping: LeavePolicyMapping, from_date: date, to_date: date) -> Tuple[float, Dict[str, Any]]:
    cal = get_employee_calendar(company_id, emp.id)
    weekend_days = set(json_load(cal.weekend_days_json if cal else None, [5, 6]))
    holidays = set()
    if cal:
        holidays = get_holidays_set(company_id, cal.id, from_date, to_date)

    working_days, excluded_days = [], []
    for d in daterange(from_date, to_date):
        if d.weekday() in weekend_days or d in holidays:
            excluded_days.append(d)
        else:
            working_days.append(d)

    meta = {
        "holiday_calendar_id": cal.id if cal else None,
        "weekend_days": sorted(list(weekend_days)),
        "working_days": len(working_days),
        "excluded_days": len(excluded_days),
        "sandwich_counted": False
    }

    unit = (mapping.unit or "DAY").upper()
    if unit == "HOUR":
        # actual hours will be calculated in routes
        return float(len(working_days)), meta

    units = float(len(working_days))
    cfg = get_policy_config(company_id, mapping.policy_id)
    if cfg.get("sandwich", False):
        units = float((to_date - from_date).days + 1)
        meta["sandwich_counted"] = True

    return units, meta

def build_workflow_steps(company_id: int, mapping: LeavePolicyMapping) -> List[str]:
    cfg = get_policy_config(company_id, mapping.policy_id)
    steps = cfg.get("workflow_roles") or ["MANAGER", "HR", "ADMIN"]
    return [str(s).upper() for s in steps]

def proration_factor(join_date: Optional[date], period_start: date, period_end: date) -> float:
    if not join_date:
        return 1.0
    if join_date <= period_start:
        return 1.0
    if join_date > period_end:
        return 0.0
    total_months = (period_end.year - period_start.year) * 12 + (period_end.month - period_start.month) + 1
    remaining_months = (period_end.year - join_date.year) * 12 + (period_end.month - join_date.month) + 1
    return max(0.0, min(1.0, remaining_months / float(total_months)))

def compute_entitlement(company_id: int, emp: Employee, mapping: LeavePolicyMapping, fiscal_start: date, fiscal_end: date) -> float:
    cfg = get_policy_config(company_id, mapping.policy_id)
    alloc = float(mapping.annual_allocation or 0.0)
    if cfg.get("proration", False):
        doj = getattr(emp, "date_of_joining", None)
        factor = proration_factor(doj, fiscal_start, fiscal_end)
        return round(alloc * factor, 2)
    return alloc

def ledger_sum(company_id: int, employee_id: int, leave_type_id: int) -> float:
    balance = db.session.query(
        func.sum(
            case(
                (LeaveLedger.txn_type.in_(("ACCRUAL", "CREDIT")), LeaveLedger.units),
                (LeaveLedger.txn_type.in_(("DEBIT", "ENCASH")), -LeaveLedger.units),
                else_=0.0
            )
        )
    ).filter(
        LeaveLedger.company_id == company_id,
        LeaveLedger.employee_id == employee_id,
        LeaveLedger.leave_type_id == leave_type_id
    ).scalar()

    return round(float(balance or 0.0), 2)

def add_ledger(company_id: int, employee_id: int, leave_type_id: int, txn_type: str, units: float, note: str, request_id: Optional[int]=None):
    db.session.add(LeaveLedger(
        company_id=company_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        request_id=request_id,
        txn_type=txn_type,
        units=float(units),
        note=note
    ))

def encash(company_id: int, employee_id: int, leave_type_id: int, units: float, note: str, amount: Optional[float]=None):
    add_ledger(company_id, employee_id, leave_type_id, "ENCASH", units, note)
    db.session.add(LeaveEncashment(
        company_id=company_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        units=float(units),
        amount=amount,
        note=note
    ))
