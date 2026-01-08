from flask import request, jsonify
from flask_login import login_required, current_user
from . import leave_bp
from .models import Leave
from models import db

@leave_bp.route('/apply', methods=['POST'])
@login_required
def apply_leave():
    data = request.get_json()
    new_leave = Leave(
        employee_id=current_user.id,
        leave_type_id=data['leave_type_id'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        reason=data['reason']
    )
    db.session.add(new_leave)
    db.session.commit()
    return jsonify({'message': 'Leave application submitted'}), 201