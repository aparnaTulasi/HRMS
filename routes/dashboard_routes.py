from flask import Blueprint, jsonify, g
from datetime import datetime, date, timedelta
from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.shift import ShiftAssignment, Shift
from models.task import Task
from models.payroll import PaySlip
from models.company import Company
from models.user import User
from leave.models import LeaveRequest, LeaveBalance, Holiday, EmployeeHolidayCalendar
from utils.decorators import token_required
from sqlalchemy import desc, func, or_
import calendar

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    # Legacy stats API
    return _get_role_dashboard_stats()

def _get_role_dashboard_stats():
    """
    Core logic for calculating dashboard stats based on user role.
    Shared by /api/dashboard/stats and /<username>/<company>/dashboard
    """
    role = (g.user.role or "").upper()
    user_id = g.user.id
    cid = g.user.company_id
    today = date.today()

    # --- 1. SUPER ADMIN DASHBOARD ---
    if role in ["SUPER_ADMIN", "SUPERADMIN"]:
        from models.branch import Branch
        total_companies = Company.query.count()
        total_branches = Branch.query.count()
        total_admins = User.query.filter_by(role="ADMIN").count()
        total_hrs = User.query.filter_by(role="HR").count()
        total_managers = User.query.filter_by(role="MANAGER").count()
        total_employees = Employee.query.count()
        active_users = User.query.filter_by(status='ACTIVE').count()
        
        # Module Usage
        payroll_usage = Company.query.filter_by(has_payroll=True).count()
        attendance_usage = Company.query.filter_by(has_attendance=True).count()
        leave_usage = Company.query.filter_by(has_leave=True).count()
        performance_usage = Company.query.filter_by(has_performance=True).count()

        # Attendance summary (for today)
        today_date = date.today()
        attendance_counts = db.session.query(Attendance.status, func.count(Attendance.attendance_id))\
            .filter(Attendance.attendance_date == today_date).group_by(Attendance.status).all()
        att_dict = {status: count for status, count in attendance_counts}
        
        # Pending Requests
        pending_leaves = LeaveRequest.query.filter_by(status='PENDING').count()
        # WFH and Expense require models not imported here yet, adding imports inside if needed or just count
        from models.hr_documents import WFHRequest
        from models.travel_expense import TravelExpense
        pending_wfh = WFHRequest.query.filter_by(status='PENDING').count()
        pending_expenses = TravelExpense.query.filter_by(status='Pending').count()

        return jsonify({
            "success": True,
            "role": "SUPER_ADMIN",
            "data": {
                "top_stats": [
                    {"label": "Total Companies", "value": total_companies, "icon": "Business"},
                    {"label": "Total Branches", "value": total_branches, "icon": "Map"},
                    {"label": "Total Users", "value": User.query.count(), "icon": "People"},
                    {"label": "Active Users", "value": active_users, "icon": "CheckCircle"}
                ],
                "stats": {
                    "total_companies": total_companies,
                    "total_branches": total_branches,
                    "total_admins": total_admins,
                    "total_hrs": total_hrs,
                    "total_managers": total_managers,
                    "total_employees": total_employees,
                    "totalCompanies": total_companies,
                    "totalBranches": total_branches,
                    "totalAdmins": total_admins,
                    "totalHrs": total_hrs,
                    "totalManagers": total_managers,
                    "totalEmployees": total_employees,
                    "active_users": active_users
                },
                "attendance_summary": [
                    {"label": "Present", "value": att_dict.get("Present", 0)},
                    {"label": "Absent", "value": att_dict.get("Absent", 0)},
                    {"label": "WFH", "value": att_dict.get("WFH", 0)},
                    {"label": "Leave", "value": att_dict.get("Leave", 0) + att_dict.get("Half Day", 0)}
                ],
                "pending_actions": {
                    "leaves": pending_leaves,
                    "wfh": pending_wfh,
                    "expenses": pending_expenses,
                    "total": pending_leaves + pending_wfh + pending_expenses
                },
                "module_usage": [
                    {"name": "Payroll", "count": payroll_usage},
                    {"name": "Attendance", "count": attendance_usage},
                    {"name": "Leave", "count": leave_usage},
                    {"name": "Performance", "count": performance_usage}
                ],
                "last_updated": datetime.now().isoformat()
            }
        })

    # --- 2. MANAGER DASHBOARD ---
    if role == "MANAGER":
        # Get team members
        team_members = Employee.query.filter_by(manager_id=user_id).all()
        team_ids = [m.id for m in team_members]
        
        # Today's Team Attendance
        att_counts = db.session.query(Attendance.status, func.count(Attendance.attendance_id))\
            .filter(Attendance.employee_id.in_(team_ids), Attendance.attendance_date == today)\
            .group_by(Attendance.status).all()
        
        att_dict = {status: count for status, count in att_counts}
        
        # Pending Approvals
        pending_leaves = LeaveRequest.query.filter(LeaveRequest.employee_id.in_(team_ids), LeaveRequest.status == 'Pending').count()

        # Generate personal stats (like employee role)
        emp = Employee.query.filter_by(user_id=user_id).first()
        status = "Absent"
        in_time = "--:--"
        out_time = "--:--"
        logged_hours = "0h 0m"
        shift_str = "No Shift Assigned"
        total_balance = 0
        personal_pending_leaves = 0
        pending_tasks = 0
        next_holiday_str = "No upcoming holidays"
        
        if emp:
            att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()
            if att:
                status = att.status
                if att.punch_in_time: in_time = att.punch_in_time.strftime("%I:%M %p")
                if att.punch_out_time: out_time = att.punch_out_time.strftime("%I:%M %p")
                total_mins = att.total_minutes
                if total_mins > 0:
                    h = total_mins // 60
                    m = total_mins % 60
                    logged_hours = f"{h}h {m}m"

            shift_assign = ShiftAssignment.query.filter_by(employee_id=emp.id).first()
            if shift_assign and shift_assign.shift:
                s = shift_assign.shift
                shift_str = f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"

            balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()
            total_balance = sum([(b.balance or 0.0) for b in balances])
            personal_pending_leaves = LeaveRequest.query.filter_by(employee_id=emp.id, status='Pending').count()
            pending_tasks = Task.query.filter_by(assigned_to_employee_id=emp.id, status='Pending').count()

            next_holiday_obj = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date).first()
            if next_holiday_obj:
                next_holiday_str = f"{next_holiday_obj.date.strftime('%b %d')} ({next_holiday_obj.name})"

        return jsonify({
            "success": True,
            "role": "MANAGER",
            "data": {
                "team_snapshot": {
                    "total_members": len(team_members),
                    "present": att_dict.get("Present", 0),
                    "absent": att_dict.get("Absent", 0),
                    "on_leave": att_dict.get("Leave", 0) + att_dict.get("Half Day", 0),
                    "late": att_dict.get("Late", 0)
                },
                "pending_actions": {
                    "approvals": pending_leaves,
                    "attendance_corrections": 0  # Placeholder if not implemented
                },
                # Add personal UI payload compatible with "My Space" and Employee Dashboard
                "at_a_glance": {
                    "status": status,
                    "shift": shift_str,
                    "in_time": in_time,
                    "out_time": out_time,
                    "logged_hours": logged_hours
                },
                "stats": {
                    "leave_balance": total_balance,
                    "pending_leaves": personal_pending_leaves,
                    "action_required_tasks": pending_tasks,
                    "next_holiday": next_holiday_str
                }
            }
        })

    # --- 3. HR DASHBOARD ---
    if role == "HR":
        total_emp = Employee.query.filter_by(company_id=cid).count()
        new_hires = Employee.query.filter(Employee.company_id == cid, func.month(Employee.date_of_joining) == today.month).count()
        
        # Today's Org Attendance
        leave_today = Attendance.query.filter(Attendance.company_id == cid, Attendance.attendance_date == today, Attendance.status.in_(['Leave', 'Half Day'])).count()

        return jsonify({
            "success": True,
            "role": "HR",
            "data": {
                "company_health": {
                    "total_employees": total_emp,
                    "new_hires_month": new_hires,
                    "on_leave_today": leave_today
                },
                "lifecycle": {
                    "onboarding_pending": 0, # Placeholder
                    "confirmation_due": 0    # Placeholder
                }
            }
        })

    # --- 4. ADMIN DASHBOARD ---
    if role == "ADMIN":
        active_emp = Employee.query.filter_by(company_id=cid, is_active=True).count()
        late_today = Attendance.query.filter(Attendance.company_id == cid, Attendance.attendance_date == today, Attendance.status == 'Late').count()

        return jsonify({
            "success": True,
            "role": "ADMIN",
            "data": {
                "operations": {
                    "active_employees": active_emp,
                    "attendance_issues": late_today,
                    "system_tasks_pending": 0
                }
            }
        })

    # --- 5. ACCOUNTANT DASHBOARD ---
    if role == "ACCOUNTANT":
        # Get current month payroll summary
        payroll_sum = db.session.query(func.sum(PaySlip.net_salary))\
            .filter(PaySlip.company_id == cid, PaySlip.pay_month == today.month, PaySlip.pay_year == today.year).scalar() or 0
        
        payroll_status = "Processing" # Logic could be more complex

        return jsonify({
            "success": True,
            "role": "ACCOUNTANT",
            "data": {
                "payroll_snapshot": {
                    "total_payout": float(payroll_sum),
                    "cycle_status": payroll_status,
                    "pending_approvals": 0
                }
            }
        })

    # --- 6. DEFAULT / EMPLOYEE DASHBOARD ---
    emp = Employee.query.filter_by(user_id=user_id).first()
    if not emp:
        return jsonify({
            "success": True,
            "role": role,
            "data": {
                "message": "Status N/A (No Employee Profile Found)"
            }
        })

    # Existing Employee logic...
    att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()
    status = "Absent"
    in_time = "--:--"
    out_time = "--:--"
    logged_hours = "0h 0m"
    
    if att:
        status = att.status
        if att.punch_in_time: in_time = att.punch_in_time.strftime("%I:%M %p")
        if att.punch_out_time: out_time = att.punch_out_time.strftime("%I:%M %p")
        total_mins = att.total_minutes
        if total_mins > 0:
            h = total_mins // 60
            m = total_mins % 60
            logged_hours = f"{h}h {m}m"

    shift_assign = ShiftAssignment.query.filter_by(employee_id=emp.id).first()
    shift_str = "No Shift Assigned"
    if shift_assign and shift_assign.shift:
        s = shift_assign.shift
        shift_str = f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"

    balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()
    total_balance = sum([(b.balance or 0.0) for b in balances])
    pending_leaves = LeaveRequest.query.filter_by(employee_id=emp.id, status='Pending').count()
    pending_tasks = Task.query.filter_by(assigned_to_employee_id=emp.id, status='Pending').count()

    next_holiday_obj = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date).first()
    next_holiday_str = "No upcoming holidays"
    if next_holiday_obj:
        next_holiday_str = f"{next_holiday_obj.date.strftime('%b %d')} ({next_holiday_obj.name})"

    return jsonify({
        "success": True,
        "role": "EMPLOYEE",
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

@dashboard_bp.route('/employee', methods=['GET'])
@token_required
def get_employee_dashboard():
    """
    Comprehensive Employee Dashboard API returning real data for the rich UI.
    """
    user_id = g.user.id
    today = date.today()
    
    emp = Employee.query.filter_by(user_id=user_id).first()
    if not emp:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404

    # 1. AT A GLANCE (Attendance & Shift)
    att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()
    status = "Absent"
    in_time = "--:--"
    out_time = "--:--"
    logged_hours = "0h 0m"
    
    if att:
        status = att.status
        if att.punch_in_time: in_time = att.punch_in_time.strftime("%I:%M %p")
        if att.punch_out_time: out_time = att.punch_out_time.strftime("%I:%M %p")
        total_mins = att.total_minutes or 0
        h = total_mins // 60
        m = total_mins % 60
        logged_hours = f"{h}h {m}m"
    elif today.weekday() >= 5: # Assuming Sat/Sun are weekends if no attendance
        status = "Weekend"

    shift_assign = ShiftAssignment.query.filter_by(employee_id=emp.id).first()
    shift_str = "General Shift"
    if shift_assign and shift_assign.shift:
        s = shift_assign.shift
        shift_str = f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"

    # 2. LEAVE BALANCE
    balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()
    total_balance = sum([(b.balance or 0.0) for b in balances])
    
    last_leave = LeaveRequest.query.filter_by(employee_id=emp.id).order_by(desc(LeaveRequest.created_at)).first()
    leave_msg = "No recent requests"
    if last_leave:
        leave_msg = f"Last Request: {last_leave.status}"
        if last_leave.status == 'Pending':
            leave_msg = "Next Leave Approval: Pending"

    # 3. ACTION REQUIRED (Tasks)
    pending_tasks_query = Task.query.filter(
        Task.assigned_to_employee_id == emp.id, 
        Task.status.in_(['Pending', 'InProgress'])
    )
    tasks_count = pending_tasks_query.count()
    latest_task = pending_tasks_query.order_by(desc(Task.created_at)).first()
    task_label = latest_task.title if latest_task else "No pending tasks"

    # 4. NEXT HOLIDAY
    # Find holiday from calendars linked to this employee
    next_holiday = db.session.query(Holiday).join(EmployeeHolidayCalendar, Holiday.calendar_id == EmployeeHolidayCalendar.calendar_id)\
        .filter(EmployeeHolidayCalendar.employee_id == emp.id, Holiday.date >= today)\
        .order_by(Holiday.date).first()
    
    if not next_holiday:
        # Fallback to any company holiday
        next_holiday = Holiday.query.filter(Holiday.company_id == emp.company_id, Holiday.date >= today)\
            .order_by(Holiday.date).first()

    holiday_data = {
        "date": next_holiday.date.strftime("%b %d") if next_holiday else "N/A",
        "name": next_holiday.name if next_holiday else "No upcoming holidays",
        "day": next_holiday.date.strftime("%a") if next_holiday else ""
    }

    # 5. SALARY TREND (Last 5 Months)
    payslips = PaySlip.query.filter_by(employee_id=emp.id)\
        .order_by(desc(PaySlip.pay_year), desc(PaySlip.pay_month))\
        .limit(5).all()
    
    month_names = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    salary_trend = []
    for ps in reversed(payslips):
        salary_trend.append({
            "month": month_names[ps.pay_month] if 1 <= ps.pay_month <= 12 else str(ps.pay_month),
            "amount": ps.net_salary
        })

    # 6. RECENT PAYSLIPS (Top 3)
    current_payslips = []
    for ps in payslips[:3]:
        current_payslips.append({
            "id": ps.id,
            "month": f"{month_names[ps.pay_month]} {ps.pay_year} Log",
            "ref": f"Ref: #PS-{ps.pay_year}-{ps.pay_month:02d}",
            "status": ps.status == "PAID"
        })

    # 7. NEXT PAY DATE
    # Default to last day of current month
    last_day = calendar.monthrange(today.year, today.month)[1]
    next_pay_date = date(today.year, today.month, last_day).strftime("%B %d, %Y")

    return jsonify({
        "success": True,
        "data": {
            "user": {
                "full_name": emp.full_name,
                "first_name": (emp.full_name.split()[0] if emp.full_name and emp.full_name.split() else "Employee")
            },
            "at_a_glance": {
                "status": status,
                "shift": shift_str,
                "timings": {"in": in_time, "out": out_time},
                "logged_hours": logged_hours,
                "date": today.strftime("%d %b %Y")
            },
            "leave_balance": {
                "days": int(total_balance),
                "message": leave_msg
            },
            "action_required": {
                "count": f"{tasks_count:02d}",
                "label": "Tasks",
                "latest_task": task_label
            },
            "next_holiday": holiday_data,
            "salary_trend": salary_trend,
            "current_payslips": current_payslips,
            "next_pay_date": next_pay_date.upper()
        }
    })
