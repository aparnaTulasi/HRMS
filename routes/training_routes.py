# routes/training_routes.py
from flask import Blueprint, request, jsonify, g
from models import db
from models.training import TrainingProgram, TrainingParticipant, TrainingMaterial
from models.employee import Employee
from utils.decorators import token_required, role_required
from utils.audit_logger import log_action
from datetime import datetime, date
import sqlalchemy as sa

training_bp = Blueprint("training", __name__)

def _company_id():
    return getattr(g, "company_id", 1)

def _user_id():
    return getattr(g, "user_id", None)

def _json_ok(data, message="Success"):
    return jsonify({"success": True, "data": data, "message": message})

@training_bp.get("/stats")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def training_stats():
    cid = _company_id()
    active_courses = TrainingProgram.query.filter_by(company_id=cid, status="In Progress").count()
    
    # Simple completion rate: avg of all participants
    avg_completion = db.session.query(sa.func.avg(TrainingParticipant.completion_rate)) \
        .join(TrainingProgram) \
        .filter(TrainingProgram.company_id == cid).scalar() or 0
        
    total_hours = db.session.query(sa.func.sum(TrainingProgram.training_hours)) \
        .filter(TrainingProgram.company_id == cid).scalar() or 0
        
    return _json_ok({
        "active_courses": active_courses,
        "completion_rate": int(avg_completion),
        "training_hours": total_hours
    })

@training_bp.get("/programs")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def training_programs_list():
    items = TrainingProgram.query.filter_by(company_id=_company_id()) \
        .order_by(TrainingProgram.start_date.desc()).all()
        
    data = []
    for x in items:
        participant_count = len(x.participants)
        data.append({
            "id": x.id,
            "title": x.title,
            "trainer_platform": x.trainer_platform,
            "start_date": x.start_date.isoformat() if x.start_date else None,
            "duration": x.duration,
            "participants": f"{participant_count} Employees",
            "status": x.status
        })
    return _json_ok(data)

@training_bp.post("/programs")
@token_required
@role_required(["HR"])
def training_program_create():
    payload = request.get_json()
    title = payload.get("title")
    start_date_str = payload.get("start_date")
    
    if not title or not start_date_str:
        return jsonify({"success": False, "message": "Title and Start Date required"}), 400
        
    prog = TrainingProgram(
        company_id=_company_id(),
        title=title,
        trainer_platform=payload.get("trainer_platform"),
        start_date=date.fromisoformat(start_date_str),
        duration=payload.get("duration"),
        training_hours=int(payload.get("training_hours", 0)),
        description=payload.get("description"),
        status=payload.get("status", "Upcoming")
    )
    db.session.add(prog)
    db.session.commit()
    
    log_action(
        action="CREATE_TRAINING_PROGRAM",
        entity="TrainingProgram",
        entity_id=prog.id,
        meta={"title": title}
    )
    
    return _json_ok({"id": prog.id}, "Training program created")

@training_bp.get("/programs/<int:pid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def training_program_details(pid):
    x = TrainingProgram.query.filter_by(id=pid, company_id=_company_id()).first()
    if not x:
        return jsonify({"success": False, "message": "Not found"}), 404
        
    enrolled = []
    for p in x.participants:
        enrolled.append({
            "id": p.id,
            "full_name": p.employee.full_name if p.employee else "Unknown",
            "completion": p.completion_rate
        })
        
    materials = []
    for m in x.materials:
        materials.append({
            "id": m.id,
            "title": m.title,
            "file_path": m.file_path,
            "file_type": m.file_type
        })
        
    return _json_ok({
        "id": x.id,
        "title": x.title,
        "trainer_platform": x.trainer_platform,
        "start_date": x.start_date.isoformat(),
        "duration": x.duration,
        "status": x.status,
        "description": x.description,
        "enrolled_employees": enrolled,
        "materials": materials
    })

@training_bp.post("/programs/<int:pid>/assign")
@token_required
@role_required(["HR"])
def training_assign_employees(pid):
    payload = request.get_json()
    employee_ids = payload.get("employee_ids", [])
    
    prog = TrainingProgram.query.get(pid)
    if not prog: return jsonify({"success": False, "message": "Program not found"}), 404
        
    count = 0
    for eid in employee_ids:
        # Check if already assigned
        existing = TrainingParticipant.query.filter_by(training_id=pid, employee_id=eid).first()
        if not existing:
            p = TrainingParticipant(training_id=pid, employee_id=eid)
            db.session.add(p)
            count += 1
            
    db.session.commit()
    
    log_action(
        action="ASSIGN_TRAINING",
        entity="TrainingProgram",
        entity_id=pid,
        meta={"assigned_count": count}
    )
    
    return _json_ok(None, f"Assigned {count} employees")

@training_bp.post("/programs/<int:pid>/materials")
@token_required
@role_required(["HR"])
def training_add_material(pid):
    payload = request.get_json()
    title = payload.get("title")
    file_path = payload.get("file_path")
    
    if not title or not file_path:
        return jsonify({"success": False, "message": "Title and File Path required"}), 400
        
    m = TrainingMaterial(
        training_id=pid,
        title=title,
        file_path=file_path,
        file_type=payload.get("file_type", "PDF")
    )
    db.session.add(m)
    db.session.commit()
    
    return _json_ok({"id": m.id}, "Material added")
