from flask import Blueprint, jsonify, g
from datetime import datetime, date, timedelta
from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.shift import ShiftAssignment, Shift
from models.task import Task
from models.payroll import PaySlip
from leave.models import LeaveRequest, LeaveBalance, Holiday
from utils.decorators import token_required
from sqlalchemy import desc

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        # Fallback for users without employee profile (e.g. Super Admin)
        return jsonify({
            "success": True,
            "data": {
                "at_a_glance": {"status": "N/A", "shift": "No Shift Assigned", "in_time": "--:--", "out_time": "--:--", "logged_hours": "0h 0m"},
                "stats": {"leave_balance": 0, "pending_leaves": 0, "action_required_tasks": 0, "next_holiday": "No upcoming holidays"}
            }
        })

    today = date.today()
    
    # 1. Attendance Data
    att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()
    status = "Absent"
    in_time = "--:--"
    out_time = "--:--"
    logged_hours = "0h 0m"
    
    if att:
        status = att.status
        if att.punch_in_time:
            in_time = att.punch_in_time.strftime("%I:%M %p")
        if att.punch_out_time:
            out_time = att.punch_out_time.strftime("%I:%M %p")
        
        # Calculate logged hours using the total_minutes property
        total_mins = att.total_minutes
        if total_mins > 0:
            h = total_mins // 60
            m = total_mins % 60
            logged_hours = f"{h}h {m}m"

    # 2. Shift Data
    shift_assign = ShiftAssignment.query.filter_by(employee_id=emp.id).first()
    shift_str = "No Shift Assigned"
    if shift_assign and shift_assign.shift:
        s = shift_assign.shift
        shift_str = f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"

    # 3. Leave Data
    # Sum up balances
    balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()
    total_balance = sum([b.balance for b in balances])
    
    pending_leaves = LeaveRequest.query.filter_by(employee_id=emp.id, status='Pending').count()

    # 4. Tasks Data
    pending_tasks = Task.query.filter_by(assigned_to_employee_id=emp.id, status='Pending').count()

    # 5. Next Holiday
    next_holiday_obj = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date).first()
    next_holiday_str = "No upcoming holidays"
    if next_holiday_obj:
        next_holiday_str = f"{next_holiday_obj.date.strftime('%b %d')} ({next_holiday_obj.name})"

    return jsonify({
        "success": True,
        "data": {
            "at_a_glance": {
                "status": status,
                "shift": shift_str,
                "in_time": in_time,
                "out_time": out_time,
                "logged_hours": logged_hours
            },
            "stats": {
                "leave_balance": total_balance,
                "pending_leaves": pending_leaves,
                "action_required_tasks": pending_tasks,
                "next_holiday": next_holiday_str
            }
        }
    })

@dashboard_bp.route('/salary-data', methods=['GET'])
@token_required
def get_salary_dashboard():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({"success": True, "data": {"salary_trend": [], "recent_payslips": []}})

    # 1. Salary Trend (Last 5 Months)
    payslips = PaySlip.query.filter_by(employee_id=emp.id)\
        .order_by(desc(PaySlip.pay_year), desc(PaySlip.pay_month))\
        .limit(5).all()
    
    # Reverse to show chronological order
    payslips = payslips[::-1]
    
    trend = []
    month_names = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    for ps in payslips:
        trend.append({
            "month": month_names[ps.pay_month] if 1 <= ps.pay_month <= 12 else str(ps.pay_month),
            "amount": ps.net_salary
        })

    # 2. Recent Payslips
    recent = []
    for ps in reversed(payslips): # Show newest first for the list
        month_label = f"{month_names[ps.pay_month]} {ps.pay_year}"
        ref_id = f"#PS-{ps.pay_year}-{ps.pay_month:02d}"
        recent.append({
            "id": ps.id,
            "month": month_label,
            "ref": ref_id,
            "status": ps.status, # e.g. FINAL, PAID
            "net_pay": ps.net_salary
        })

    return jsonify({
        "success": True,
        "data": {
            "salary_trend": trend,
            "recent_payslips": recent[:3] # Top 3
        }
    })
