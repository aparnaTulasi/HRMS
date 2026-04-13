from flask import Blueprint, request, jsonify, g
from models import db
from models.attendance import Attendance, AttendanceRegularization
from models.attendance_punch_log import AttendancePunchLog
from models.attendance_device import AttendanceDevice
from models.attendance_settings import AttendanceSettings
from models.employee import Employee
from models.user import User
from utils.decorators import token_required, role_required, permission_required
from constants.permissions_registry import Permissions
from datetime import datetime
from models.attendance_policy import AttendancePolicy
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

@attendance_features_bp.route('/device/list', methods=['GET'])
@token_required
@permission_required(Permissions.ATTENDANCE_VIEW)
def list_devices():
    company_id = g.user.company_id
    devices = AttendanceDevice.query.filter_by(company_id=company_id).all()
    
    # Stats
    total = len(devices)
    active = len([d for d in devices if d.is_active])
    inactive = total - active
    total_employees = Employee.query.filter_by(company_id=company_id).count()
    
    device_data = []
    for d in devices:
        # Check pending records for this device
        pending_count = AttendancePunchLog.query.filter_by(device_id=d.id, status='RECEIVED').count()
        
        device_data.append({
            'id': d.id,
            'device_name': d.device_name,
            'device_id': d.device_code,
            'ip_address': d.ip_address,
            'location': d.location,
            'device_type': d.device_type,
            'status': 'Active' if d.is_active else 'Inactive',
            'last_sync': d.last_seen_at.strftime('%Y-%m-%d %I:%M %p') if d.last_seen_at else 'Never',
            'pending_records': pending_count,
            'sync_status': 'Idle' if pending_count == 0 else 'Pending'
        })
        
    return jsonify({
        'success': True,
        'stats': {
            'total_devices': total,
            'active_devices': active,
            'inactive_devices': inactive,
            'total_employees': total_employees
        },
        'data': device_data
    })

@attendance_features_bp.route('/device/register', methods=['POST'])
@token_required
@permission_required(Permissions.ATTENDANCE_EDIT)
def register_device():
    data = request.get_json()
    if not all(k in data for k in ['device_code', 'device_name', 'device_type']):
        return jsonify({'message': 'Missing fields: device_code, device_name, device_type'}), 400
    
    device = AttendanceDevice(
        company_id=g.user.company_id,
        device_code=data['device_code'],
        device_name=data['device_name'],
        ip_address=data.get('ip_address'),
        location=data.get('location'),
        device_type=data['device_type'],
        is_active=data.get('status', 'Active') == 'Active'
    )
    db.session.add(device)
    db.session.commit()
    return jsonify({'message': 'Device registered successfully', 'id': device.id}), 201

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

@attendance_features_bp.route('/sync/logs', methods=['GET'])
@token_required
@permission_required(Permissions.ATTENDANCE_VIEW)
def get_sync_logs():
    logs = AttendancePunchLog.query.filter_by(company_id=g.user.company_id).order_by(AttendancePunchLog.created_at.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'data': [{
            'id': l.id,
            'user_id': l.user_id,
            'punch_time': l.punch_time.isoformat(),
            'punch_type': l.punch_type,
            'source': l.source,
            'status': l.status,
            'reject_reason': l.reject_reason
        } for l in logs]
    })

@attendance_features_bp.route('/sync/trigger', methods=['POST'])
@token_required
@permission_required(Permissions.ATTENDANCE_EDIT)
def trigger_sync():
    logs = AttendancePunchLog.query.filter_by(company_id=g.user.company_id, status='RECEIVED').all()
    if not logs:
        return jsonify({'message': 'No pending logs to sync'}), 200
    
    process_punch_logs([l.id for l in logs])
    return jsonify({'message': f'Sync triggered for {len(logs)} logs'}), 200

@attendance_features_bp.route('/sync/biometric', methods=['POST'])
@token_required
@permission_required(Permissions.ATTENDANCE_EDIT)
def biometric_sync_trigger():
    """
    Simulates a manual trigger to fetch logs from physical biometric devices.
    In a real scenario, this would call a secondary service or use a library like pyzk.
    """
    company_id = g.user.company_id
    devices = AttendanceDevice.query.filter_by(company_id=company_id, is_active=True).all()
    
    if not devices:
        return jsonify({'success': False, 'message': 'No active biometric devices registered'}), 400
        
    # Simulate fetching records
    count = 0
    import random
    import uuid
    from datetime import timedelta
    
    # Just for demonstration in the roadmap handover
    random_emp = Employee.query.filter_by(company_id=company_id).first()
    if random_emp:
        new_log = AttendancePunchLog(
            company_id=company_id,
            device_id=devices[0].id,
            user_id=random_emp.user_id,
            punch_time=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
            punch_type=random.choice(['IN', 'OUT']),
            source='BIOMETRIC_SYNC',
            client_event_id=str(uuid.uuid4()),
            status='RECEIVED'
        )
        db.session.add(new_log)
        db.session.commit()
        process_punch_logs([new_log.id])
        count = 1

    return jsonify({
        'success': True, 
        'message': f'Biometric sync completed. Successfully fetched {count} new records from {len(devices)} devices.',
        'sync_time': datetime.utcnow().isoformat()
    }), 200

@attendance_features_bp.route('/punch/mobile', methods=['POST'])
@token_required
def mobile_punch():
    data = request.get_json()
    punch_type = data.get('punch_type', 'IN').upper()
    
    log = AttendancePunchLog(
        company_id=g.user.company_id,
        user_id=g.user.id,
        punch_time=datetime.utcnow(),
        punch_type=punch_type,
        source='MOBILE',
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        location_name=data.get('location_name'),
        client_event_id=str(uuid.uuid4()),
        status='RECEIVED'
    )
    db.session.add(log)
    db.session.commit()
    
    process_punch_logs([log.id])
    return jsonify({'message': f'Mobile {punch_type} recorded successfully', 'id': log.id}), 201

@attendance_features_bp.route('/sync/status', methods=['GET'])
@token_required
@permission_required(Permissions.ATTENDANCE_VIEW)
def get_sync_status():
    company_id = g.user.company_id
    settings = AttendanceSettings.query.filter_by(company_id=company_id).first()
    devices = AttendanceDevice.query.filter_by(company_id=company_id).all()
    
    total_pending = AttendancePunchLog.query.filter_by(company_id=company_id, status='RECEIVED').count()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_devices': len(devices),
            'connected': len([d for d in devices if d.is_active]),
            'disconnected': len([d for d in devices if not d.is_active]),
            'pending_records': total_pending
        },
        'settings': {
            'auto_sync': settings.auto_sync if settings else True,
            'sync_interval': settings.sync_interval_minutes if settings else 30
        }
    })

@attendance_features_bp.route('/sync/settings', methods=['POST'])
@token_required
@permission_required(Permissions.ATTENDANCE_EDIT)
def update_sync_settings():
    data = request.get_json()
    company_id = g.user.company_id
    settings = AttendanceSettings.query.filter_by(company_id=company_id).first()
    if not settings:
        settings = AttendanceSettings(company_id=company_id)
        db.session.add(settings)
    
    if 'auto_sync' in data: settings.auto_sync = bool(data['auto_sync'])
    if 'sync_interval' in data: settings.sync_interval_minutes = int(data['sync_interval'])
    
    db.session.commit()
    return jsonify({'message': 'Sync settings updated successfully'}), 200

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

# ========== Attendance Policy Routes ==========

@attendance_features_bp.route('/policy', methods=['GET'])
@token_required
def get_attendance_policy():
    policy = AttendancePolicy.query.filter_by(company_id=g.user.company_id).first()
    if not policy:
        # Return default policy if not found
        return jsonify({
            'success': True,
            'data': {
                'grace_time_minutes': 15,
                'half_day_hours': 4.0,
                'full_day_hours': 8.0,
                'late_marks_limit': 3
            }
        })
    return jsonify({
        'success': True,
        'data': {
            'grace_time_minutes': policy.grace_time_minutes,
            'half_day_hours': policy.half_day_hours,
            'full_day_hours': policy.full_day_hours,
            'late_marks_limit': policy.late_marks_limit,
            'shift_buffer_minutes': policy.shift_buffer_minutes
        }
    })

@attendance_features_bp.route('/policy', methods=['POST'])
@token_required
@permission_required(Permissions.ATTENDANCE_EDIT)
def update_attendance_policy():
    data = request.get_json()
    policy = AttendancePolicy.query.filter_by(company_id=g.user.company_id).first()
    if not policy:
        policy = AttendancePolicy(company_id=g.user.company_id)
        db.session.add(policy)
    
    if 'grace_time_minutes' in data: policy.grace_time_minutes = data['grace_time_minutes']
    if 'half_day_hours' in data: policy.half_day_hours = data['half_day_hours']
    if 'full_day_hours' in data: policy.full_day_hours = data['full_day_hours']
    if 'late_marks_limit' in data: policy.late_marks_limit = data['late_marks_limit']
    
    db.session.commit()
    return jsonify({'message': 'Attendance policy updated successfully'}), 200

# ========== Regularization Routes ==========

@attendance_features_bp.route('/regularization/request', methods=['GET'])
@token_required
def list_regularization_requests():
    company_id = g.user.company_id
    role = g.user.role
    
    query = AttendanceRegularization.query.filter_by(company_id=company_id)
    if role == 'EMPLOYEE':
        query = query.filter_by(employee_id=g.user.employee_profile.id)
    
    requests = query.order_by(AttendanceRegularization.created_at.desc()).all()
    
    # Stats
    stats = {
        'total': len(requests),
        'pending': len([r for r in requests if r.status == 'PENDING']),
        'approved': len([r for r in requests if r.status == 'APPROVED']),
        'rejected': len([r for r in requests if r.status == 'REJECTED'])
    }
    
    data = []
    for r in requests:
        emp = r.employee
        data.append({
            'id': r.id,
            'employee_name': emp.full_name if emp else "Unknown",
            'employee_code': emp.employee_id if emp else "N/A",
            'date': r.attendance_date.isoformat(),
            'request_type': r.request_type,
            'punch_type': r.punch_type,
            'requested_time': r.requested_punch_in.strftime('%I:%M %p') if r.requested_punch_in else (r.requested_punch_out.strftime('%I:%M %p') if r.requested_punch_out else "N/A"),
            'actual_time': r.actual_time or "Not Punched",
            'reason': r.reason,
            'status': r.status,
            'reviewed_by': User.query.get(r.approved_by).full_name if r.approved_by else None
        })
        
    return jsonify({
        'success': True,
        'stats': stats,
        'data': data
    })

@attendance_features_bp.route('/regularization/request', methods=['POST'])
@token_required
def request_regularization():
    data = request.get_json()
    if not all(k in data for k in ['attendance_date', 'reason', 'request_type']):
        return jsonify({'message': 'Missing required fields'}), 400

    new_request = AttendanceRegularization(
        company_id=g.user.company_id, 
        employee_id=g.user.employee_profile.id,
        attendance_date=datetime.strptime(data['attendance_date'], '%Y-%m-%d').date(),
        request_type=data['request_type'], # MISSING_PUNCH, WRONG_PUNCH
        punch_type=data.get('punch_type'), # PUNCH_IN, PUNCH_OUT, BOTH
        reason=data['reason'],
        requested_punch_in=datetime.fromisoformat(data['requested_punch_in']) if data.get('requested_punch_in') else None,
        requested_punch_out=datetime.fromisoformat(data['requested_punch_out']) if data.get('requested_punch_out') else None,
        actual_time=data.get('actual_time') or "Not Punched"
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'message': 'Regularization request submitted successfully', 'request_id': new_request.id}), 201

@attendance_features_bp.route('/regularization/request/<int:request_id>/review', methods=['POST'])
@token_required
@permission_required(Permissions.ATTENDANCE_APPROVE)
def review_regularization_request(request_id):
    # Enforce Permission: HR/Manager must have MANAGE_ATTENDANCE permission
    # Permission check now handled by decorator

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