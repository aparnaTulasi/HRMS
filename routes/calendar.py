from flask import Blueprint, request, jsonify, g
from models import db
from models.calendar_event import CalendarEvent
from utils.decorators import token_required
from datetime import datetime

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/events', methods=['GET'])
@token_required
def get_events():
    try:
        # Super Admin sees all (or specific logic based on needs, maybe only their own or system wide)
        if g.user.role == 'SUPER_ADMIN':
            # For this scenario, maybe Super Admin sees everything or just company=1
            events = CalendarEvent.query.all()
        else:
            # Admins, HR, Employees see events for their company
            events = CalendarEvent.query.filter_by(company_id=g.user.company_id).all()
            
        return jsonify([e.to_dict() for e in events]), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Failed to fetch events', 'error': str(e)}), 500

@calendar_bp.route('/events', methods=['POST'])
@token_required
def create_event():
    # RBAC constraint: Only Super Admin and Admin can create
    if g.user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized to create events'}), 403

    data = request.get_json()
    try:
        date_obj = datetime.strptime(data.get('date'), '%Y-%m-%d').date() if data.get('date') else None
        
        new_event = CalendarEvent(
            title=data.get('title'),
            date=date_obj,
            start_time=data.get('startTime'),
            end_time=data.get('endTime'),
            type=data.get('type', 'work'),
            description=data.get('description'),
            company_id=g.user.company_id if g.user.role != 'SUPER_ADMIN' else data.get('company_id', 1),
            created_by=g.user.id
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'message': 'Event created successfully', 'event': new_event.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Failed to create event', 'error': str(e)}), 500

@calendar_bp.route('/events/<int:id>', methods=['PUT', 'PATCH'])
@token_required
def update_event(id):
    if g.user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized to edit events'}), 403

    data = request.get_json()
    try:
        event = CalendarEvent.query.filter_by(id=id).first()
        if not event:
            return jsonify({'message': 'Event not found'}), 404
            
        # Security check: Ensure Admin is only editing within their company
        if g.user.role == 'ADMIN' and event.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized to edit this event'}), 403
            
        if 'title' in data: event.title = data['title']
        if 'date' in data and data['date']: 
            event.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'startTime' in data: event.start_time = data['startTime']
        if 'endTime' in data: event.end_time = data['endTime']
        if 'type' in data: event.type = data['type']
        if 'description' in data: event.description = data['description']
            
        db.session.commit()
        return jsonify({'message': 'Event updated successfully', 'event': event.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update event', 'error': str(e)}), 500

@calendar_bp.route('/events/<int:id>', methods=['DELETE'])
@token_required
def delete_event(id):
    if g.user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized to delete events'}), 403

    try:
        event = CalendarEvent.query.filter_by(id=id).first()
        if not event:
            return jsonify({'message': 'Event not found'}), 404
            
        if g.user.role == 'ADMIN' and event.company_id != g.user.company_id:
            return jsonify({'message': 'Unauthorized to delete this event'}), 403
            
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': 'Event deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete event', 'error': str(e)}), 500
