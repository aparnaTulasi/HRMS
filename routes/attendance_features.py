from flask import Blueprint, request, jsonify, g
from models import db
from models.attendance_device import AttendanceDevice
from models.attendance_punch_log import AttendancePunchLog
from models.attendance import Attendance
from models.regularization import AttendanceRegularization
from models.user import User
from utils.decorators import token_required, role_required
from datetime import datetime
import uuid

attendance_features_bp = Blueprint('attendance_features', __name__, url_prefix='/api/attendance/features')

# ========== Device Health Routes ==========

@attendance_features_bp.route('/device/heartbeat', methods=['POST'])
@token_required # A device-specific token might be better, but this is fine for now.
def device_heartbeat():
    data = request.get_json()
    device_code = data.get('device_code')
    # Assuming the token belongs to a user associated with the device.
    company_id = g.user.company_id 

    if not device_code:
        return jsonify({'message': 'Device code is required'}), 400

    device = AttendanceDevice.query.filter_by(device_code=device_code, company_id=company_id).first()
    if not device:
        # For now, we assume devices are pre-registered.
        return jsonify({'message': 'Device not registered'}), 404

    device.last_seen_at = datetime.utcnow()
    device.last_ip = request.remote_addr
    device.battery_percent = data.get('battery_percent')
    device.storage_percent = data.get('storage_percent')
    device.app_version = data.get('app_version')
    
    db.session.commit()
    
    return jsonify({'message': 'Heartbeat received successfully'}), 200

# ========== Offline Sync Routes ==========

@attendance_features_bp.route('/punch/batch-upload', methods=['POST'])
@token_required
def batch_punch_upload():
    data = request.get_json()
    punches = data.get('punches', [])
    offline_batch_id = data.get('offline_batch_id', str(uuid.uuid4()))
    
    if not punches:
        return jsonify({'message': 'No punches in batch'}), 400

    company_id = g.user.company_id
    device_id = data.get('device_id') # Device should send its DB id.

    new_logs = []
    rejected_logs = []

    for punch in punches:
        if not all(k in punch for k in ['user_id', 'punch_time', 'punch_type', 'client_event_id']):
            rejected_logs.append({'client_event_id': punch.get('client_event_id'), 'reason': 'Missing required fields'})
            continue

        if AttendancePunchLog.query.filter_by(company_id=company_id, client_event_id=punch['client_event_id']).first():
            rejected_logs.append({'client_event_id': punch['client_event_id'], 'reason': 'Duplicate client_event_id'})
            continue

        new_log = AttendancePunchLog(
            company_id=company_id,
            device_id=device_id,
            user_id=punch['user_id'],
            punch_time=datetime.fromisoformat(punch['punch_time']),
            punch_type=punch['punch_type'].upper(),
            source=punch.get('source', 'DEVICE'),
            offline_batch_id=offline_batch_id,
            client_event_id=punch['client_event_id'],
            status='RECEIVED'
        )
        new_logs.append(new_log)

    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()
        
        # In a production environment, this should be a background task (e.g., Celery).
        process_punch_logs([log.id for log in new_logs])

    return jsonify({
        'message': 'Batch processed',
        'processed_count': len(new_logs),
        'rejected_count': len(rejected_logs),
        'rejected_logs': rejected_logs
    }), 202

def process_punch_logs(log_ids):
    """Processes raw punch logs and updates the main attendance table."""
    logs = AttendancePunchLog.query.filter(AttendancePunchLog.id.in_(log_ids)).all()
    
    for log in logs:
        try:
            user = User.query.get(log.user_id)
            if not user or not user.employee_profile:
                log.status = 'REJECTED'
                log.reject_reason = 'User or employee profile not found'
                db.session.commit()
                continue

            employee_id = user.employee_profile.id
            punch_date = log.punch_time.date()

            attendance_record = Attendance.query.filter_by(employee_id=employee_id, date=punch_date).first()
            if not attendance_record:
                attendance_record = Attendance(employee_id=employee_id, date=punch_date, year=punch_date.year, month=punch_date.month, marked_by='SYSTEM')
                db.session.add(attendance_record)
                db.session.flush()

            if log.punch_type == 'IN' and (not attendance_record.in_time or log.punch_time < attendance_record.in_time):
                attendance_record.in_time = log.punch_time
            elif log.punch_type == 'OUT' and (not attendance_record.out_time or log.punch_time > attendance_record.out_time):
                attendance_record.out_time = log.punch_time
            
            if attendance_record.in_time:
                attendance_record.status = 'PRESENT'
                if attendance_record.out_time:
                    duration = attendance_record.out_time - attendance_record.in_time
                    attendance_record.work_hours = round(duration.total_seconds() / 3600, 2)

            log.status = 'PROCESSED'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.status = 'REJECTED'
            log.reject_reason = str(e)
            db.session.add(log)
            db.session.commit()

# ========== Regularization Routes ==========

@attendance_features_bp.route('/regularization/request', methods=['POST'])
@token_required
def request_regularization():
    data = request.get_json()
    if not all(k in data for k in ['attendance_date', 'reason']):
        return jsonify({'message': 'Missing required fields: attendance_date, reason'}), 400

    new_request = AttendanceRegularization(
        company_id=g.user.company_id, user_id=g.user.id,
        attendance_date=datetime.strptime(data['attendance_date'], '%Y-%m-%d').date(),
        reason=data['reason'],
        requested_login_at=datetime.fromisoformat(data['requested_login_at']) if data.get('requested_login_at') else None,
        requested_logout_at=datetime.fromisoformat(data['requested_logout_at']) if data.get('requested_logout_at') else None,
        requested_status=data.get('requested_status')
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'message': 'Regularization request submitted', 'request_id': new_request.id}), 201

@attendance_features_bp.route('/regularization/request/<int:request_id>/review', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR', 'MANAGER'])
def review_regularization_request(request_id):
    # Enforce Permission: HR/Manager must have MANAGE_ATTENDANCE permission
    if g.user.role not in ['SUPER_ADMIN', 'ADMIN'] and not g.user.has_permission('MANAGE_ATTENDANCE'):
        return jsonify({'message': 'Permission denied: MANAGE_ATTENDANCE required'}), 403

    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ['APPROVED', 'REJECTED']:
        return jsonify({'message': 'Invalid status. Must be APPROVED or REJECTED'}), 400

    req = AttendanceRegularization.query.get_or_404(request_id)
    if req.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403

    req.status = new_status
    req.reviewed_by = g.user.id
    req.review_comment = data.get('review_comment')
    
    if new_status == 'APPROVED':
        employee = User.query.get(req.user_id).employee_profile
        att_rec = Attendance.query.filter_by(employee_id=employee.id, date=req.attendance_date).first()
        if not att_rec:
            att_rec = Attendance(company_id=employee.company_id, employee_id=employee.id, date=req.attendance_date, year=req.attendance_date.year, month=req.attendance_date.month, marked_by='REGULARIZATION')
            db.session.add(att_rec)

        if req.requested_login_at: att_rec.in_time = req.requested_login_at
        if req.requested_logout_at: att_rec.out_time = req.requested_logout_at
        if req.requested_status: att_rec.status = req.requested_status
        
        if att_rec.in_time and att_rec.out_time:
            att_rec.work_hours = round((att_rec.out_time - att_rec.in_time).total_seconds() / 3600, 2)
        elif att_rec.status != 'ABSENT':
             att_rec.status = 'PRESENT'

    db.session.commit()
    return jsonify({'message': f'Request has been {new_status.lower()}'}), 200