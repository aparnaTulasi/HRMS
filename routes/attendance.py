from flask import Blueprint, jsonify, request, g
from datetime import datetime, date
from models import db
from models.attendance import Attendance
from models.employee import Employee
from utils.decorators import token_required

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/mark-in', methods=['POST'])
@token_required
def mark_in_time():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    today = date.today()
    existing = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    if existing and existing.in_time: return jsonify({'message': 'Already marked in for today'}), 400
    
    if existing:
        existing.in_time = datetime.utcnow()
        existing.status = 'PRESENT'
    else:
        attendance = Attendance(employee_id=emp.id, date=today, in_time=datetime.utcnow(), status='PRESENT')
        db.session.add(attendance)
    db.session.commit()
    return jsonify({'message': 'In time marked successfully'})