from flask import Blueprint, request, jsonify, g
from models import db
from models.shift import Shift, ShiftAssignment
from utils.decorators import token_required, role_required
from datetime import datetime

shift_bp = Blueprint('shift', __name__)

@shift_bp.route('/', methods=['GET'])
@token_required
def get_shifts():
    shifts = Shift.query.filter_by(company_id=g.user.company_id).all()
    output = []
    for s in shifts:
        output.append({
            'shift_id': s.shift_id,
            'shift_name': s.shift_name,
            'start_time': s.start_time.strftime('%H:%M:%S') if s.start_time else None,
            'end_time': s.end_time.strftime('%H:%M:%S') if s.end_time else None,
            'weekly_off': s.weekly_off,
            'is_active': s.is_active
        })
    return jsonify(output)

@shift_bp.route('/', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_shift():
    data = request.get_json()
    try:
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
    except ValueError:
        return jsonify({'message': 'Invalid time format. Use HH:MM'}), 400

    new_shift = Shift(
        company_id=g.user.company_id,
        shift_name=data['shift_name'],
        start_time=start_time,
        end_time=end_time,
        weekly_off=data.get('weekly_off', 'Sunday'),
        description=data.get('description')
    )
    db.session.add(new_shift)
    db.session.commit()
    return jsonify({'message': 'Shift created successfully'}), 201