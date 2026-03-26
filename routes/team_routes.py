from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.squad import Squad
from models.squad_member import SquadMember
from models.user import User
from utils.decorators import token_required
from datetime import date, datetime, timedelta
from sqlalchemy import func
import random

team_bp = Blueprint('team', __name__)

@team_bp.route('/api/superadmin/team/dashboard', methods=['GET'])
@token_required
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

@team_bp.route('/api/superadmin/squads', methods=['POST'])
@token_required
def build_squad():
    data = request.get_json()
    
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = data.get('company_id', 1)

    new_squad = Squad(
        company_id=company_id,
        squad_name=data.get('squad_name'),
        project_name=data.get('project_name'),
        squad_type=data.get('squad_type', 'IT'),
        status='Active'
    )
    
    db.session.add(new_squad)
    db.session.flush()
    
    # Add members if provided
    members = data.get('members', [])
    for m in members:
        member = SquadMember(
            squad_id=new_squad.id,
            employee_id=m.get('employee_id'),
            role=m.get('role', 'Member')
        )
        db.session.add(member)
        
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Squad created successfully",
        "data": new_squad.to_dict()
    }), 201
