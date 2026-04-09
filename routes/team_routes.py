from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.squad import Squad
from models.squad_member import SquadMember
from models.user import User
from utils.decorators import token_required, role_required
from datetime import date, datetime, timedelta
from sqlalchemy import func, or_
import random

team_bp = Blueprint('team', __name__)

@team_bp.route('/api/superadmin/team/dashboard', methods=['GET'])
@token_required
@role_required(['HR'])
def get_team_dashboard():
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)

    # 1. Total Members
    total_members = Employee.query.filter_by(company_id=company_id).count()

    # 2. Today's Attendance Stats
    today = date.today()
    attendance = Attendance.query.filter_by(company_id=company_id, attendance_date=today).all()
    
    present_now = len([a for a in attendance if a.status == 'Present'])
    on_leave = len([a for a in attendance if a.status in ['Leave', 'Half Day']])
    remote_wfh = len([a for a in attendance if a.status == 'WFH'])

    return jsonify({
        "success": True,
        "data": {
            "total_members": total_members,
            "present_now": present_now,
            "on_leave": on_leave,
            "remote_wfh": remote_wfh,
            "trends": {
                "members": "+3 since last month",
                "present": "95% vs last month",
                "on_leave": "-1 vs last month",
                "remote": "+2 vs last month"
            }
        }
    })

@team_bp.route('/api/superadmin/team/superstars', methods=['GET'])
@token_required
@role_required(['HR'])
def get_team_superstars():
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)

    # Get top 6 employees (mocking performance via random for now)
    employees = Employee.query.filter_by(company_id=company_id).limit(6).all()
    
    superstars = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        superstars.append({
            "id": emp.id,
            "name": emp.full_name,
            "role": emp.designation or "Team Member",
            "image": user.profile_pic if user and hasattr(user, 'profile_pic') else None,
            "performance": random.randint(85, 98),
            "status": "online" # Mock status
        })

    return jsonify({
        "success": True,
        "data": superstars
    })

@team_bp.route('/api/superadmin/team/resilience', methods=['GET'])
@token_required
@role_required(['HR'])
def get_team_resilience():
    # Mock data for the graph as requested (inspired by "graph database" concept)
    return jsonify({
        "success": True,
        "data": {
            "consistency_score": [78, 82, 85, 80, 88, 92, 90, 94, 91, 95],
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
            "metrics": {
                "current": "94%",
                "average": "87%",
                "peak": "98%"
            }
        }
    })

@team_bp.route('/api/superadmin/squads', methods=['GET'])
@token_required
@role_required(['HR'])
def get_squads():
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)

    total_squads = Squad.query.filter_by(company_id=company_id).count()
    it_squads = Squad.query.filter_by(company_id=company_id, squad_type='IT').all()
    non_it_squads = Squad.query.filter_by(company_id=company_id, squad_type='Non-IT').all()
    active_projects = db.session.query(func.count(func.distinct(Squad.project_name))).filter_by(company_id=company_id).scalar()

    return jsonify({
        "success": True,
        "data": {
            "stats": {
                "total_squads": total_squads,
                "it_squads_count": len(it_squads),
                "non_it_squads_count": len(non_it_squads),
                "active_projects": active_projects or 0
            },
            "it_squads": [s.to_dict() for s in it_squads],
            "non_it_squads": [s.to_dict() for s in non_it_squads]
        }
    })

@team_bp.route('/api/team/squads/form-options', methods=['GET'])
@token_required
@role_required(['HR'])
def get_squad_form_options():
    # In a real app, these could come from a Master table. 
    # For now, providing based on the UI requirements.
    return jsonify({
        "success": True,
        "data": {
            "departments": ["IT Department", "Non-IT Department"],
            "squad_types": ["General Team", "Project Wise"]
        }
    })

@team_bp.route('/api/team/squads/employees', methods=['GET'])
@token_required
@role_required(['HR'])
def get_squad_employees():
    company_id = g.user.company_id
    search = request.args.get('search', '')
    
    query = Employee.query.filter_by(company_id=company_id)
    if search:
        query = query.filter(Employee.full_name.ilike(f"%{search}%"))
        
    employees = query.all()
    data = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        data.append({
            "id": emp.id,
            "name": emp.full_name,
            "designation": emp.designation,
            "image": user.profile_pic if user and hasattr(user, 'profile_pic') else None
        })
        
    return jsonify({
        "success": True,
        "data": data
    })

@team_bp.route('/api/superadmin/squads', methods=['POST'])
@token_required
@role_required(['HR'])
def build_squad():
    data = request.get_json()
    
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = data.get('company_id', 1)

    new_squad = Squad(
        company_id=company_id,
        squad_name=data.get('squad_name'),
        project_name=data.get('project_name'),
        department=data.get('department', 'IT Department'),
        squad_type=data.get('squad_type', 'General Team'),
        status='Active'
    )
    
    db.session.add(new_squad)
    db.session.flush()
    
    # Add members if provided
    members = data.get('members', []) # Expected list of {"employee_id": 1, "role": "Lead"} 
    # Or just member_ids list
    member_ids = data.get('member_ids', [])
    
    for m in members:
        member = SquadMember(
            squad_id=new_squad.id,
            employee_id=m.get('employee_id'),
            role=m.get('role', 'Member')
        )
        db.session.add(member)
        
    for eid in member_ids:
        # Check if already added via members list
        if not any(m.get('employee_id') == eid for m in members):
            member = SquadMember(
                squad_id=new_squad.id,
                employee_id=eid,
                role='Member'
            )
            db.session.add(member)
        
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Squad created successfully",
        "data": new_squad.to_dict()
    }), 201

# --- Employee Team View Endpoints (Read-Only) ---

@team_bp.route('/api/team/employee/dashboard', methods=['GET'])
@token_required
def get_employee_team_dashboard():
    """
    Stats for the employee's squad or department.
    """
    emp = g.user.employee_profile
    if not emp:
        return jsonify({"success": False, "message": "Employee profile required"}), 400
        
    cid = g.user.company_id
    
    # Identify Squad
    sq_member = SquadMember.query.filter_by(employee_id=emp.id).first()
    sq_id = sq_member.squad_id if sq_member else None
    
    if sq_id:
        # Team is the Squad
        member_ids = [m.employee_id for m in SquadMember.query.filter_by(squad_id=sq_id).all()]
        total_members = len(member_ids)
        
        # Today's attendance in squad
        today = date.today()
        attendance = Attendance.query.filter(
            Attendance.employee_id.in_(member_ids),
            Attendance.attendance_date == today
        ).all()
        
        active_now = len([a for a in attendance if a.status in ['Present', 'WFH']])
        
        # Pending Onboarding or Leave
        pending = len([a for a in attendance if a.status == 'Leave']) # Simplified
        
        # Admins in squad (User role in ['ADMIN', 'HR', 'SUPER_ADMIN'] or Squad Lead role)
        admins_count = SquadMember.query.filter(
            SquadMember.squad_id == sq_id,
            or_(SquadMember.role == 'Lead', SquadMember.role == 'Manager')
        ).count()
        
    else:
        # If not in a squad, show nothing or just department stats
        total_members = 0
        active_now = 0
        pending = 0
        admins_count = 0
        
    return jsonify({
        "success": True,
        "data": {
            "total_members": total_members,
            "active_now": active_now,
            "pending": pending,
            "admins_count": admins_count,
            "trends": {
                "members": "+0 vs last month",
                "active": "0% vs last month",
                "pending": "0 vs last month",
                "admins": "0 vs last month"
            }
        }
    })

@team_bp.route('/api/team/employee/superstars', methods=['GET'])
@token_required
def get_employee_team_superstars():
    """
    Lists the current employee's squad members.
    """
    emp = g.user.employee_profile
    if not emp:
        return jsonify({"success": True, "data": []}), 200
        
    sq_member = SquadMember.query.filter_by(employee_id=emp.id).first()
    if not sq_member:
        return jsonify({"success": True, "data": []}), 200
        
    members = SquadMember.query.filter_by(squad_id=sq_member.squad_id).all()
    
    superstars = []
    for m in members:
        e = m.employee # Relation defined in SquadMember
        if not e: continue
        
        user = User.query.get(e.user_id)
        superstars.append({
            "id": e.id,
            "name": e.full_name,
            "role": m.role or e.designation or "Team Member",
            "image": user.profile_pic if user and hasattr(user, 'profile_pic') else None,
            "performance": random.randint(85, 98),
            "status": "online" # Mock
        })
        
    return jsonify({"success": True, "data": superstars})

@team_bp.route('/api/team/employee/resilience', methods=['GET'])
@token_required
def get_employee_team_resilience():
    """
    Consistency/Resilience data for the squad.
    """
    return jsonify({
        "success": True,
        "data": {
            "consistency_score": [75, 80, 82, 79, 85, 90, 88, 92, 89, 94],
            "labels": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7", "Day 8", "Day 9", "Day 10"],
            "metrics": {
                "current": "94%",
                "average": "82%",
                "peak": "98%"
            }
        }
    })
@team_bp.route('/api/manager/team/dashboard', methods=['GET'])
@token_required
@role_required(['MANAGER'])
def get_manager_team_dashboard():
    """Stats for the Manager's squad(s)."""
    emp = g.user.employee_profile
    if not emp:
        return jsonify({"success": False, "message": "Employee profile required"}), 400
        
    cid = g.user.company_id
    
    # 1. Identify Squad(s) managed by this user
    # Managers are often identified either by being the Squad lead or by direct reports
    managed_squads = SquadMember.query.filter(
        SquadMember.employee_id == emp.id,
        or_(SquadMember.role == 'Lead', SquadMember.role == 'Manager')
    ).all()
    
    squad_ids = [s.squad_id for s in managed_squads]
    
    if squad_ids:
        # Team is the Squad members
        members = SquadMember.query.filter(SquadMember.squad_id.in_(squad_ids)).all()
        member_ids = list(set([m.employee_id for m in members]))
        total_members = len(member_ids)
        
        # Today's attendance
        today = date.today()
        attendance = Attendance.query.filter(
            Attendance.employee_id.in_(member_ids),
            Attendance.attendance_date == today
        ).all()
        
        active_now = len([a for a in attendance if a.status in ['Present', 'WFH']])
        
        # Pending Onboarding/Leaves
        pending = len([a for a in attendance if a.status == 'Leave'])
        
        # Admins (Leads/Managers in these squads)
        admins_count = SquadMember.query.filter(
            SquadMember.squad_id.in_(squad_ids),
            or_(SquadMember.role == 'Lead', SquadMember.role == 'Manager', SquadMember.role == 'Admin')
        ).count()
    else:
        # Fallback to direct reports if no squads managed
        # Use existing logic from dashboard or simple check
        from models.employee import Employee
        reports = Employee.query.filter_by(manager_id=g.user.id).all()
        total_members = len(reports)
        active_now = 0 # Placeholder for direct reports attendance if not in squad
        pending = 0
        admins_count = 0

    return jsonify({
        "success": True,
        "data": {
            "total_members": total_members,
            "active_now": active_now,
            "pending": pending,
            "admins_count": admins_count,
            "trends": {
                "members": "+0 vs last month",
                "active": "0% vs last month",
                "pending": "0 vs last month",
                "admins": "+0 vs last month"
            }
        }
    })

@team_bp.route('/api/manager/team/superstars', methods=['GET'])
@token_required
@role_required(['MANAGER'])
def get_manager_team_superstars():
    """Lists superstar members of the Manager's squad."""
    emp = g.user.employee_profile
    if not emp: return jsonify({"success": True, "data": []}), 200
    
    managed_squads = SquadMember.query.filter(
        SquadMember.employee_id == emp.id,
        or_(SquadMember.role == 'Lead', SquadMember.role == 'Manager')
    ).all()
    
    squad_ids = [s.squad_id for s in managed_squads]
    if not squad_ids:
        # Fallback to direct reports
        employees = Employee.query.filter_by(manager_id=g.user.id).all()
    else:
        members = SquadMember.query.filter(SquadMember.squad_id.in_(squad_ids)).all()
        emp_ids = list(set([m.employee_id for m in members]))
        employees = Employee.query.filter(Employee.id.in_(emp_ids)).all()

    superstars = []
    for e in employees:
        user = User.query.get(e.user_id)
        # Mocking performance based on attendance consistency for a more real feel
        performance = random.randint(88, 99) if e.status == 'ACTIVE' else random.randint(70, 85)
        
        superstars.append({
            "id": e.id,
            "name": e.full_name,
            "role": e.designation or "Team Member",
            "image": user.profile_pic if user and hasattr(user, 'profile_pic') else None,
            "performance": performance,
            "status": "online" if e.status == 'ACTIVE' else "offline"
        })
        
    return jsonify({"success": True, "data": superstars})

@team_bp.route('/api/manager/team/resilience', methods=['GET'])
@token_required
@role_required(['MANAGER'])
def get_manager_team_resilience():
    """Monthly consistency/resilience data for the team."""
    # Data following the dashboard resilience format
    return jsonify({
        "success": True,
        "data": {
            "consistency_score": [82, 85, 87, 84, 89, 93, 91, 95, 92, 94],
            "labels": ["Day 1", "Day 5", "Day 10", "Day 15", "Day 20", "Day 25", "Day 26", "Day 27", "Day 28", "Today"],
            "metrics": {
                "current": "94%",
                "average": "88%",
                "peak": "98%"
            }
        }
    })
