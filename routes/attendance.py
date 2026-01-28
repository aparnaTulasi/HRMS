from flask import Blueprint, jsonify, request, g
from datetime import datetime, date
from models import db
from models.attendance import Attendance
from models.employee import Employee
from utils.decorators import token_required, role_required

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

@attendance_bp.route('/mark-out', methods=['POST'])
@token_required
def mark_out_time():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp: return jsonify({'message': 'Employee not found'}), 404
    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    
    if not attendance or not attendance.in_time:
        return jsonify({'message': 'You have not marked in today'}), 400
    
    attendance.out_time = datetime.utcnow()
    # Calculate work hours (simple difference)
    duration = attendance.out_time - attendance.in_time
    attendance.work_hours = round(duration.total_seconds() / 3600, 2)
    
    db.session.commit()
    return jsonify({'message': 'Out time marked successfully'})

@attendance_bp.route('/correction', methods=['POST'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def correct_attendance():
    data = request.get_json()
    employee_id = data.get('employee_id')
    date_str = data.get('date')
    
    if not employee_id or not date_str:
        return jsonify({'message': 'Missing employee_id or date'}), 400
        
    attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    attendance = Attendance.query.filter_by(employee_id=employee_id, date=attendance_date).first()
    
    if not attendance:
        attendance = Attendance(employee_id=employee_id, date=attendance_date)
        db.session.add(attendance)
    
    if 'in_time' in data:
        attendance.in_time = datetime.strptime(data['in_time'], '%Y-%m-%d %H:%M:%S')
    if 'out_time' in data:
        attendance.out_time = datetime.strptime(data['out_time'], '%Y-%m-%d %H:%M:%S')
    
    attendance.status = data.get('status', attendance.status)
    attendance.remarks = data.get('remarks', attendance.remarks)
        
    db.session.commit()
    return jsonify({'message': 'Attendance updated successfully'})