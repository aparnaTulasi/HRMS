from flask import Blueprint, request, jsonify, g
from models import db
from models.employee import Employee
from models.attendance import Attendance
from leave.models import LeaveRequest
from utils.decorators import token_required, role_required

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/team', methods=['GET'])
@token_required
@role_required(['MANAGER', 'ADMIN', 'HR', 'SUPER_ADMIN'])
def get_team_members():
    # If not Admin/HR, filter by manager_id
    q = Employee.query.filter_by(company_id=g.user.company_id)
    
    if g.user.role == 'MANAGER':
        q = q.filter_by(manager_id=g.user.id)
    
    employees = q.all()
    
    return jsonify({
        "success": True,
        "count": len(employees),
        "team": [{
            "id": e.id,
            "employee_id": e.employee_id,
            "name": e.full_name,
            "department": e.department,
            "designation": e.designation,
            "status": e.status
        } for e in employees]
    })

@manager_bp.route('/team/attendance', methods=['GET'])
@token_required
@role_required(['MANAGER'])
def get_team_attendance():
    from datetime import date
    today = date.today()
    
    # Get team members
    team = Employee.query.filter_by(manager_id=g.user.id, is_active=True).all()
    team_ids = [e.id for e in team]
    
    if not team_ids:
        return jsonify({"success": True, "attendance": []})
        
    attendances = Attendance.query.filter(
        Attendance.employee_id.in_(team_ids),
        Attendance.attendance_date == today
    ).all()
    
    # Map by employee ID
    att_map = {a.employee_id: a for a in attendances}
    
    output = []
    for e in team:
        att = att_map.get(e.id)
        output.append({
            "name": e.full_name,
            "employee_id": e.employee_id,
            "status": att.status if att else "Not Logged Today",
            "in_time": att.punch_in_time.strftime("%I:%M %p") if att and att.punch_in_time else "--",
            "out_time": att.punch_out_time.strftime("%I:%M %p") if att and att.punch_out_time else "--"
        })
        
    return jsonify({"success": True, "attendance": output})

@manager_bp.route('/pending-requests', methods=['GET'])
@token_required
@role_required(['MANAGER'])
def get_pending_requests():
    # Get team members
    team = Employee.query.filter_by(manager_id=g.user.id).all()
    team_ids = [e.id for e in team]
    
    if not team_ids:
        return jsonify({"success": True, "leaves": [], "attendance_regularizations": []})
        
    # Pending Leaves
    leaves = LeaveRequest.query.filter(
        LeaveRequest.employee_id.in_(team_ids),
        LeaveRequest.status == 'Pending'
    ).all()
    
    # We might need to handle AttendanceRegularization here too if the model is available
    # For now, let's return leaves
    
    return jsonify({
        "success": True,
        "leaves": [{
            "id": l.id,
            "employee_name": l.employee.full_name,
            "leave_type": l.leave_type,
            "from_date": l.from_date.strftime("%Y-%m-%d"),
            "to_date": l.to_date.strftime("%Y-%m-%d"),
            "days": l.total_days,
            "reason": l.reason
        } for l in leaves]
    })
