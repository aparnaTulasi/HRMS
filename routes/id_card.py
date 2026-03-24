from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.id_card import IDCard, IDCardHistory
from utils.decorators import token_required
from utils.qr_service import generate_id_card_qr
from datetime import datetime, timedelta

id_card_bp = Blueprint('id_card', __name__)

@id_card_bp.route('/employee/<int:employee_id>', methods=['GET'])
@token_required
def get_employee_for_id_card(employee_id):
    emp = Employee.query.get(employee_id)
    if not emp:
        return jsonify({'success': False, 'message': 'Employee not found'}), 404
    
    # In this DB, emp.employee_id field often contains the human-readable code
    return jsonify({
        'success': True,
        'data': {
            'full_name': emp.full_name,
            'employee_code': emp.employee_id,
            'department': emp.department,
            'designation': emp.designation,
            'joining_date': emp.date_of_joining.isoformat() if emp.date_of_joining else "",
            'photo_url': getattr(emp, 'photo_url', None)
        }
    })

@id_card_bp.route('/create', methods=['POST'])
@token_required
def create_id_card():
    data = request.get_json() or {}
    employee_id = data.get('employee_id')
    
    if not employee_id:
        return jsonify({'success': False, 'message': 'employee_id is required'}), 400
        
    emp = Employee.query.get(employee_id)
    if not emp:
        return jsonify({'success': False, 'message': 'Employee not found'}), 404
        
    # Generate Unique Card ID
    card_id = f"IDC-{emp.employee_id}-{datetime.now().strftime('%y%m%d%H%H')}"
    
    # Generate QR
    qr_path = generate_id_card_qr(card_id, emp.id, emp.employee_id, data.get('company_name', 'Future Invo'))
    
    card = IDCard(
        employee_id=emp.id,
        employee_code=emp.employee_id,
        full_name=emp.full_name,
        designation=emp.designation,
        department=emp.department,
        company_name=data.get('company_name', 'Future Invo'),
        company_logo_url=data.get('company_logo_url'),
        blood_group=data.get('blood_group'),
        joining_date=emp.date_of_joining,
        emergency_contact=data.get('emergency_contact'),
        card_id=card_id,
        qr_code_path=qr_path,
        status='ACTIVE',
        expiry_date=datetime.utcnow() + timedelta(days=365*5)
    )
    
    db.session.add(card)
    db.session.flush()
    
    # Log History
    history = IDCardHistory(
        id_card_id=card.id,
        action_type='CREATED',
        reason='Initial Issue',
        new_qr_code=qr_path,
        action_by=g.user.id
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'ID Card created successfully', 
        'data': {
            'id': card.id,
            'card_id': card_id, 
            'qr_path': qr_path
        }
    })

@id_card_bp.route('/list', methods=['GET'])
@token_required
def list_id_cards():
    company_id = g.user.company_id
    cards = IDCard.query.join(Employee).filter(Employee.company_id == company_id).order_by(IDCard.id.desc()).all()
    
    return jsonify({
        'success': True,
        'data': [{
            'id': c.id,
            'employee_id': c.employee_id,
            'employee_code': c.employee_code,
            'full_name': c.full_name,
            'designation': c.designation,
            'department': c.department,
            'company_name': c.company_name,
            'company_logo_url': c.company_logo_url,
            'status': c.status,
            'card_id': c.card_id,
            'qr_path': c.qr_code_path,
            'blood_group': c.blood_group,
            'joining_date': c.joining_date.isoformat() if c.joining_date else None,
            'emergency_contact': c.emergency_contact
        } for c in cards]
    })

@id_card_bp.route('/<int:card_record_id>/mark-lost', methods=['PUT'])
@token_required
def mark_lost(card_record_id):
    card = IDCard.query.get(card_record_id)
    if not card:
        return jsonify({'success': False, 'message': 'Card not found'}), 404
        
    card.status = 'LOST'
    
    history = IDCardHistory(
        id_card_id=card.id,
        action_type='LOST_MARKED',
        reason=request.get_json().get('reason', 'Reported lost'),
        action_by=g.user.id
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Card marked as lost'})

@id_card_bp.route('/<int:card_record_id>', methods=['PUT'])
@token_required
def update_id_card(card_record_id):
    card = IDCard.query.get(card_record_id)
    if not card:
        return jsonify({'success': False, 'message': 'Card not found'}), 404
        
    data = request.get_json() or {}
    
    # Updateable fields
    fields = [
        'full_name', 'designation', 'department', 'company_name', 
        'blood_group', 'emergency_contact', 'photo_url', 'company_logo_url'
    ]
    
    for field in fields:
        if field in data:
            setattr(card, field, data.get(field))
            
    if data.get('joining_date'):
        card.joining_date = datetime.strptime(data['joining_date'], "%Y-%m-%d").date()
        
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'ID Card updated successfully',
        'data': {
            'id': card.id,
            'full_name': card.full_name,
            'card_id': card.card_id
        }
    })

@id_card_bp.route('/reissue', methods=['POST'])
@token_required
def reissue_card():
    data = request.get_json() or {}
    old_card_id = data.get('old_card_record_id')
    
    old_card = IDCard.query.get(old_card_id)
    if not old_card:
        return jsonify({'success': False, 'message': 'Old card not found'}), 404
        
    # Deactivate old
    old_card.status = 'REISSUED'
    
    # Create new
    emp = Employee.query.get(old_card.employee_id)
    new_card_id = f"IDC-{emp.employee_id}-{datetime.now().strftime('%y%m%d%H%M')}"
    new_qr_path = generate_id_card_qr(new_card_id, emp.id, emp.employee_id, old_card.company_name)
    
    new_card = IDCard(
        employee_id=emp.id,
        employee_code=emp.employee_id,
        full_name=emp.full_name,
        designation=emp.designation,
        department=emp.department,
        company_name=old_card.company_name,
        blood_group=old_card.blood_group,
        joining_date=emp.date_of_joining,
        card_id=new_card_id,
        qr_code_path=new_qr_path,
        status='ACTIVE',
        expiry_date=datetime.utcnow() + timedelta(days=365*5)
    )
    db.session.add(new_card)
    db.session.flush()
    
    # Log History
    history = IDCardHistory(
        id_card_id=new_card.id,
        action_type='REISSUED',
        reason=data.get('reason', 'Reissue requested'),
        old_qr_code=old_card.qr_code_path,
        new_qr_code=new_qr_path,
        action_by=g.user.id
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Card reissued successfully', 
        'data': {
            'card_id': new_card_id, 
            'qr_path': new_qr_path
        }
    })

@id_card_bp.route('/verify/<string:card_id>', methods=['GET'])
def verify_card(card_id):
    card = IDCard.query.filter_by(card_id=card_id).first()
    if not card:
        return jsonify({'success': False, 'message': 'Invalid Card'}), 404
        
    return jsonify({
        'success': True,
        'status': card.status,
        'data': {
            'full_name': card.full_name,
            'employee_code': card.employee_code,
            'designation': card.designation,
            'department': card.department,
            'company': card.company_name
        }
    })
