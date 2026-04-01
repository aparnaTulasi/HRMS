from flask import request, jsonify, g
from datetime import datetime
import json
from . import leave_bp
from .models import LeaveType, LeavePolicy, LeavePolicyMapping, LeaveRequest, HolidayCalendar, Holiday, EmployeeHolidayCalendar, LeaveBalance, LeaveLedger, LeaveEncashment
from .services import select_policy_mapping, compute_entitlement, add_ledger, encash
from .audit_logger import log_action
from models import db
from models.employee import Employee
from models.user import User
from models.audit_log import AuditLog
from utils.decorators import token_required, role_required
from utils.date_utils import parse_date
from sqlalchemy import func, case

# _parse_date removed to use central parse_date

# Helper to serialize model objects into dictionaries
def serialize(model_instance):
    if isinstance(model_instance, LeaveType):
        return {
            'id': model_instance.id, 'company_id': model_instance.company_id,
            'code': model_instance.code, 'name': model_instance.name,
            'unit': model_instance.unit, 'allow_half_day': model_instance.allow_half_day,
            'is_paid': model_instance.is_paid, 'is_active': model_instance.is_active,
        }
    if isinstance(model_instance, LeavePolicy):
        config = {}
        if model_instance.config_json:
            try:
                config = json.loads(model_instance.config_json)
            except (json.JSONDecodeError, TypeError):
                config = {}
        return {
            'id': model_instance.id, 'company_id': model_instance.company_id,
            'name': model_instance.name,
            'effective_from': model_instance.effective_from.isoformat() if model_instance.effective_from else None,
            'effective_to': model_instance.effective_to.isoformat() if model_instance.effective_to else None,
            'config': config, 'is_active': model_instance.is_active,
        }
    if isinstance(model_instance, LeavePolicyMapping):
        return {
            'id': model_instance.id, 'policy_id': model_instance.policy_id,
            'leave_type_id': model_instance.leave_type_id,
            'annual_allocation': model_instance.annual_allocation, 'unit': model_instance.unit,
            'allow_half_day': model_instance.allow_half_day,
            'carry_forward_limit': model_instance.carry_forward_limit,
            'encashment_limit': model_instance.encashment_limit,
        }
    if isinstance(model_instance, HolidayCalendar):
        return {
            'id': model_instance.id, 'company_id': model_instance.company_id,
            'name': model_instance.name,
            'timezone': model_instance.timezone,
            'weekend_days': json.loads(model_instance.weekend_days_json) if model_instance.weekend_days_json else [],
            'is_active': model_instance.is_active,
        }
    if isinstance(model_instance, Holiday):
        return {
            'id': model_instance.id, 'calendar_id': model_instance.calendar_id,
            'date': model_instance.date.isoformat(),
            'name': model_instance.name,
            'is_optional': model_instance.is_optional,
        }
    if isinstance(model_instance, LeaveLedger):
        return {
            'id': model_instance.id,
            'employee_id': model_instance.employee_id,
            'leave_type_id': model_instance.leave_type_id,
            'request_id': model_instance.request_id,
            'txn_type': model_instance.txn_type,
            'units': model_instance.units,
            'note': model_instance.note,
            'created_at': model_instance.created_at.isoformat() if model_instance.created_at else None
        }
    if isinstance(model_instance, LeaveRequest):
        return {
            'id': model_instance.id,
            'employee_id': model_instance.employee_id,
            'leave_type_id': model_instance.leave_type_id,
            'from_date': model_instance.from_date.isoformat() if model_instance.from_date else None,
            'to_date': model_instance.to_date.isoformat() if model_instance.to_date else None,
            'reason': model_instance.reason,
            'is_half_day': getattr(model_instance, 'is_half_day', False),
            'attachment_url': getattr(model_instance, 'attachment_url', None),
            'status': model_instance.status
        }
    if isinstance(model_instance, LeaveEncashment):
        return {
            'id': model_instance.id,
            'employee_id': model_instance.employee_id,
            'leave_type_id': model_instance.leave_type_id,
            'units': model_instance.units,
            'amount': model_instance.amount,
            'note': model_instance.note,
            'created_at': model_instance.created_at.isoformat() if getattr(model_instance, 'created_at', None) else None
        }
    return None

# ==============================================================================
# System / Maintenance Routes
# ==============================================================================

@leave_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'module': 'leave'}), 200

@leave_bp.route('/seed/defaults', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def seed_defaults():
    # Support Super Admin seeding for specific company
    company_id = request.args.get('company_id', type=int)
    if not company_id:
        company_id = g.user.company_id
        
    if not company_id:
        return jsonify({'message': 'company_id is required for seeding'}), 400
    
    # 1. Create Default Leave Types if none exist
    if not LeaveType.query.filter_by(company_id=company_id).first():
        defaults = [
            # Paid / Regular
            {'code': 'CL', 'name': 'Casual Leave (CL)', 'unit': 'DAY', 'is_paid': True},
            {'code': 'SL', 'name': 'Sick Leave (SL)', 'unit': 'DAY', 'is_paid': True},
            {'code': 'EL', 'name': 'Earned Leave / Privilege Leave (EL/PL)', 'unit': 'DAY', 'is_paid': True},
            {'code': 'AL', 'name': 'Annual Leave', 'unit': 'DAY', 'is_paid': True},
            {'code': 'CO', 'name': 'Compensatory Off (Comp Off)', 'unit': 'DAY', 'is_paid': True},
            
            # Unpaid / Special
            {'code': 'LWP', 'name': 'Leave Without Pay (LWP)', 'unit': 'DAY', 'is_paid': False},
            {'code': 'WFH', 'name': 'Work From Home (WFH)', 'unit': 'DAY', 'is_paid': True},
            
            # Women / Family
            {'code': 'ML', 'name': 'Maternity Leave', 'unit': 'DAY', 'is_paid': True},
            {'code': 'PL', 'name': 'Paternity Leave', 'unit': 'DAY', 'is_paid': True},
            {'code': 'MAR', 'name': 'Marriage Leave', 'unit': 'DAY', 'is_paid': True},
            {'code': 'BL', 'name': 'Bereavement Leave', 'unit': 'DAY', 'is_paid': True},
            {'code': 'MEN', 'name': 'Menstrual Leave', 'unit': 'DAY', 'is_paid': True},
            
            # Business / Other
            {'code': 'OD', 'name': 'On Duty / Official Duty (OD)', 'unit': 'DAY', 'is_paid': True},
            {'code': 'CMP', 'name': 'Compassionate Leave', 'unit': 'DAY', 'is_paid': True},
            {'code': 'STU', 'name': 'Study Leave', 'unit': 'DAY', 'is_paid': True},
        ]
        for d in defaults:
            db.session.add(LeaveType(company_id=company_id, **d))
        db.session.commit()
    
    # 2. Create Default Policy if none exist
    policy = LeavePolicy.query.filter_by(company_id=company_id).first()
    if not policy:
        policy = LeavePolicy(
            company_id=company_id,
            name="Standard Policy",
            effective_from=datetime.utcnow().date(),
            config_json=json.dumps({"sandwich": False, "proration": True})
        )
        db.session.add(policy)
        db.session.commit()

    # 3. Map Types to Policy if not mapped
    leave_types = LeaveType.query.filter_by(company_id=company_id).all()
    for lt in leave_types:
        if not LeavePolicyMapping.query.filter_by(policy_id=policy.id, leave_type_id=lt.id).first():
            mapping = LeavePolicyMapping(
                company_id=company_id,
                policy_id=policy.id,
                leave_type_id=lt.id,
                annual_allocation=12.0 if lt.code != 'LWP' else 0,
                unit=lt.unit,
                allow_half_day=True
            )
            db.session.add(mapping)
    
    # 4. Create Default Holiday Calendar
    if not HolidayCalendar.query.filter_by(company_id=company_id).first():
        cal = HolidayCalendar(
            company_id=company_id,
            name="General Holiday Calendar",
            weekend_days_json=json.dumps([5, 6]) # Sat, Sun
        )
        db.session.add(cal)

    db.session.commit()
    return jsonify({'message': 'Default leave configurations seeded successfully'}), 201

# ==============================================================================
# A) Leave Types Master APIs
# ==============================================================================

@leave_bp.route('/types', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_leave_type():
    data = request.get_json()
    company_id = g.user.company_id
    if not all(k in data for k in ['code', 'name']):
        return jsonify({'message': 'Missing required fields: code, name'}), 400
    if LeaveType.query.filter_by(company_id=company_id, code=data['code']).first():
        return jsonify({'message': f"Leave type with code '{data['code']}' already exists"}), 409
    new_type = LeaveType(
        company_id=company_id, code=data['code'], name=data['name'],
        unit=data.get('unit', 'DAY'), allow_half_day=data.get('allow_half_day', False),
        is_paid=data.get('is_paid', True)
    )
    db.session.add(new_type)
    db.session.commit()
    return jsonify({'message': 'Leave type created successfully', 'leave_type': serialize(new_type)}), 201

@leave_bp.route('/types', methods=['GET'])
@token_required
def list_leave_types():
    company_id = request.args.get('company_id')
    if g.user.role == 'SUPER_ADMIN' and company_id:
        try:
            target_company_id = int(company_id)
        except ValueError:
            target_company_id = g.user.company_id
    else:
        target_company_id = g.user.company_id

    print(f"DEBUG: Fetching leave types for company_id: {target_company_id}")
    types = LeaveType.query.filter_by(company_id=target_company_id, is_active=True).all()
    print(f"DEBUG: Found {len(types)} active leave types")
    return jsonify([serialize(t) for t in types]), 200

@leave_bp.route('/types/<int:id>', methods=['GET'])
@token_required
def get_leave_type(id):
    leave_type = LeaveType.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    return jsonify(serialize(leave_type)), 200

@leave_bp.route('/types/<int:id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_leave_type(id):
    leave_type = LeaveType.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    data = request.get_json()
    if 'name' in data: leave_type.name = data['name']
    if 'allow_half_day' in data: leave_type.allow_half_day = data['allow_half_day']
    if 'is_active' in data: leave_type.is_active = data['is_active']
    db.session.commit()
    return jsonify({'message': 'Leave type updated successfully', 'leave_type': serialize(leave_type)}), 200

@leave_bp.route('/types/<int:id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR'])
def delete_leave_type(id):
    leave_type = LeaveType.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    leave_type.is_active = False # Soft delete
    db.session.commit()
    return jsonify({'message': 'Leave type disabled successfully'}), 200

# ==============================================================================
# B) Leave Policies (Rules Container)
# ==============================================================================

@leave_bp.route('/policies', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_policy():
    data = request.get_json()
    if not data.get('name') or not data.get('effective_from'):
        return jsonify({'message': 'Missing required fields: name, effective_from'}), 400
    effective_from = parse_date(data['effective_from'])
    if not effective_from:
        return jsonify({'message': 'Invalid effective_from date format. Use YYYY-MM-DD.'}), 400
    new_policy = LeavePolicy(
        company_id=g.user.company_id, name=data['name'], effective_from=effective_from,
        effective_to=parse_date(data.get('effective_to')), config_json=json.dumps(data.get('config', {}))
    )
    db.session.add(new_policy)
    db.session.commit()
    return jsonify({'message': 'Leave policy created successfully', 'policy': serialize(new_policy)}), 201

@leave_bp.route('/policies', methods=['GET'])
@token_required
def list_policies():
    policies = LeavePolicy.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([serialize(p) for p in policies]), 200

@leave_bp.route('/policies/<int:id>', methods=['GET'])
@token_required
def get_policy(id):
    policy = LeavePolicy.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    return jsonify(serialize(policy)), 200

@leave_bp.route('/policies/<int:id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_policy(id):
    policy = LeavePolicy.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    data = request.get_json()
    
    if 'name' in data: 
        policy.name = data['name']
    
    if 'config' in data:
        current_config = {}
        if policy.config_json:
            try:
                current_config = json.loads(policy.config_json)
            except (json.JSONDecodeError, TypeError):
                current_config = {}
        if isinstance(data['config'], dict):
            current_config.update(data['config'])
        else:
            current_config = data['config']
        policy.config_json = json.dumps(current_config)
    
    if 'effective_to' in data:
        policy.effective_to = parse_date(data['effective_to']) if data.get('effective_to') else None
    
    if 'is_active' in data:
        policy.is_active = data['is_active']
    
    policy.updated_at = datetime.utcnow()
    db.session.commit()
    db.session.expire(policy)
    policy = LeavePolicy.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    return jsonify({'message': 'Policy updated successfully', 'policy': serialize(policy)}), 200

@leave_bp.route('/policies/<int:id>/toggle', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def toggle_policy(id):
    policy = LeavePolicy.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    data = request.get_json()
    if 'is_active' not in data:
        return jsonify({'message': 'is_active field is required'}), 400
    policy.is_active = data['is_active']
    db.session.commit()
    status = "activated" if policy.is_active else "deactivated"
    return jsonify({'message': f'Policy {status} successfully'}), 200

# ==============================================================================
# C) Policy Mapping (Policy ↔ LeaveType allocation/limits)
# ==============================================================================

@leave_bp.route('/policies/map', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def map_policy_to_leave_type():
    data = request.get_json()
    required = ['policy_id', 'leave_type_id', 'annual_allocation']
    if not all(k in data for k in required):
        return jsonify({'message': 'Missing required fields: policy_id, leave_type_id, annual_allocation'}), 400
    if not LeavePolicy.query.filter_by(id=data['policy_id'], company_id=g.user.company_id).first():
        return jsonify({'message': 'Policy not found or access denied'}), 404
    if not LeaveType.query.filter_by(id=data['leave_type_id'], company_id=g.user.company_id).first():
        return jsonify({'message': 'Leave type not found or access denied'}), 404
    if LeavePolicyMapping.query.filter_by(policy_id=data['policy_id'], leave_type_id=data['leave_type_id']).first():
        return jsonify({'message': 'This leave type is already mapped to this policy'}), 409
    new_mapping = LeavePolicyMapping(
        company_id=g.user.company_id, policy_id=data['policy_id'], leave_type_id=data['leave_type_id'],
        annual_allocation=data['annual_allocation'], unit=data.get('unit', 'DAY'),
        allow_half_day=data.get('allow_half_day', False),
        carry_forward_limit=data.get('carry_forward_limit', 0),
        encashment_limit=data.get('encashment_limit', 0)
    )
    db.session.add(new_mapping)
    db.session.commit()
    return jsonify({'message': 'Mapping created successfully', 'mapping': serialize(new_mapping)}), 201

@leave_bp.route('/policies/<int:policy_id>/mappings', methods=['GET'])
@token_required
def list_policy_mappings(policy_id):
    if not LeavePolicy.query.filter_by(id=policy_id, company_id=g.user.company_id).first():
        return jsonify({'message': 'Policy not found or access denied'}), 404
    mappings = LeavePolicyMapping.query.filter_by(policy_id=policy_id).all()
    return jsonify([serialize(m) for m in mappings]), 200

@leave_bp.route('/policies/mappings/<int:mapping_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_mapping(mapping_id):
    mapping = db.session.query(LeavePolicyMapping).join(LeavePolicy).filter(
        LeavePolicyMapping.id == mapping_id, LeavePolicy.company_id == g.user.company_id
    ).first_or_404()
    data = request.get_json()
    if 'annual_allocation' in data: mapping.annual_allocation = data['annual_allocation']
    if 'carry_forward_limit' in data: mapping.carry_forward_limit = data['carry_forward_limit']
    db.session.commit()
    return jsonify({'message': 'Mapping updated successfully', 'mapping': serialize(mapping)}), 200

@leave_bp.route('/policies/mappings/<int:mapping_id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR'])
def remove_mapping(mapping_id):
    mapping = db.session.query(LeavePolicyMapping).join(LeavePolicy).filter(
        LeavePolicyMapping.id == mapping_id, LeavePolicy.company_id == g.user.company_id
    ).first_or_404()
    db.session.delete(mapping)
    db.session.commit()
    return jsonify({'message': 'Mapping removed successfully'}), 200

# ==============================================================================
# UI-Facing Unified Policies (LeaveType + Mapping)
# ==============================================================================

@leave_bp.route('/ui-policies', methods=['GET'])
@token_required
def get_ui_policies():
    company_id = g.user.company_id or request.args.get('company_id') or 1
    # Get active default policy for company
    policy = LeavePolicy.query.filter_by(company_id=company_id, is_active=True).first()
    if not policy:
        return jsonify([])
    
    # Get mappings
    mappings = LeavePolicyMapping.query.filter_by(policy_id=policy.id).all()
    results = []
    for m in mappings:
        lt = LeaveType.query.filter_by(id=m.leave_type_id, is_active=True).first()
        if lt:
            created_by_name = 'System'
            if getattr(lt, 'created_by', None):
                user = db.session.query(User).get(lt.created_by)
                if user:
                    created_by_name = getattr(user, 'username', getattr(user, 'email', 'Admin'))
            
            results.append({
                'id': lt.id,
                'name': lt.name,
                'days': m.annual_allocation,
                'carryForward': (m.carry_forward_limit or 0) > 0,
                'maxCarryForward': m.carry_forward_limit or 0,
                'description': f"{lt.name} Policy Settings",
                'createdAt': lt.created_at.isoformat() if hasattr(lt, 'created_at') and lt.created_at else None,
                'createdBy': created_by_name
            })
    return jsonify(results), 200

@leave_bp.route('/ui-policies', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_ui_policy():
    data = request.get_json()
    company_id = g.user.company_id or data.get('company_id') or 1
    
    # Needs a default policy
    policy = LeavePolicy.query.filter_by(company_id=company_id, is_active=True).first()
    if not policy:
        # Auto-create if not exists
        policy = LeavePolicy(
            company_id=company_id,
            name="Standard Policy",
            effective_from=datetime.utcnow().date(),
            config_json="{}"
        )
        db.session.add(policy)
        db.session.flush()

    name = data.get('name')
    if not name:
        return jsonify({'message': 'Policy Name is required'}), 400
        
    code = "".join([c for c in name if c.isupper()] or name[:3]).upper()
    # Ensure code is unique
    base_code = code
    counter = 1
    while LeaveType.query.filter_by(company_id=company_id, code=code).first():
        code = f"{base_code}{counter}"
        counter += 1

    # 1. Create LeaveType
    new_type = LeaveType(
        company_id=company_id,
        code=code,
        name=name,
        unit='DAY',
        is_paid=True,
        created_at=datetime.utcnow(),
        created_by=g.user.id
    )
    db.session.add(new_type)
    db.session.flush() # get ID
    
    # 2. Map LeaveType to Policy
    days = data.get('days', 0)
    carry_forward = data.get('carryForward', False)
    max_cf = data.get('maxCarryForward', 0) if carry_forward else 0
    
    new_mapping = LeavePolicyMapping(
        company_id=company_id,
        policy_id=policy.id,
        leave_type_id=new_type.id,
        annual_allocation=days,
        carry_forward_limit=max_cf,
        unit='DAY'
    )
    db.session.add(new_mapping)
    db.session.commit()
    
    return jsonify({
        'id': new_type.id,
        'name': new_type.name,
        'days': new_mapping.annual_allocation,
        'carryForward': (new_mapping.carry_forward_limit or 0) > 0,
        'maxCarryForward': new_mapping.carry_forward_limit or 0,
        'description': f"{new_type.name} Policy Settings",
        'createdAt': new_type.created_at.isoformat() if hasattr(new_type, 'created_at') and new_type.created_at else None,
        'createdBy': 'You'
    }), 201

@leave_bp.route('/ui-policies/<int:id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_ui_policy(id):
    company_id = g.user.company_id
    data = request.get_json()
    
    # Update LeaveType
    lt = LeaveType.query.filter_by(id=id, company_id=company_id).first_or_404()
    if 'name' in data:
        lt.name = data['name']
        
    # Update Mapping
    policy = LeavePolicy.query.filter_by(company_id=company_id, is_active=True).first()
    if policy:
        mapping = LeavePolicyMapping.query.filter_by(policy_id=policy.id, leave_type_id=lt.id).first()
        if mapping:
            if 'days' in data:
                mapping.annual_allocation = data['days']
            if 'carryForward' in data or 'maxCarryForward' in data:
                cf = data.get('carryForward', (mapping.carry_forward_limit or 0) > 0)
                mapping.carry_forward_limit = data.get('maxCarryForward', mapping.carry_forward_limit) if cf else 0
    db.session.commit()
    
    return jsonify({'message': 'Updated successfully'}), 200

@leave_bp.route('/ui-policies/<int:id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR'])
def delete_ui_policy(id):
    company_id = g.user.company_id
    lt = LeaveType.query.filter_by(id=id, company_id=company_id).first_or_404()
    lt.is_active = False
    
    policy = LeavePolicy.query.filter_by(company_id=company_id, is_active=True).first()
    if policy:
        mapping = LeavePolicyMapping.query.filter_by(policy_id=policy.id, leave_type_id=lt.id).first()
        if mapping:
            db.session.delete(mapping)
    
    db.session.commit()
    return jsonify({'message': 'Deleted successfully'}), 200

# ==============================================================================
# D) Holiday Calendars & Holidays
# ==============================================================================

@leave_bp.route('/holidays/calendars', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_holiday_calendar():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'message': 'Missing required field: name'}), 400
    
    weekend_days = data.get('weekend_days', [])
    
    new_calendar = HolidayCalendar(
        company_id=g.user.company_id,
        name=data['name'],
        timezone=data.get('timezone', 'Asia/Kolkata'),
        weekend_days_json=json.dumps(weekend_days)
    )
    db.session.add(new_calendar)
    db.session.commit()
    return jsonify({'message': 'Holiday calendar created successfully', 'calendar': serialize(new_calendar)}), 201

@leave_bp.route('/holidays/calendars', methods=['GET'])
@token_required
def list_holiday_calendars():
    calendars = HolidayCalendar.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([serialize(c) for c in calendars]), 200

@leave_bp.route('/holidays/calendars/<int:id>', methods=['GET'])
@token_required
def get_holiday_calendar(id):
    calendar = HolidayCalendar.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    return jsonify(serialize(calendar)), 200

@leave_bp.route('/holidays/calendars/<int:id>', methods=['PUT'])
@token_required
@role_required(['ADMIN', 'HR'])
def update_holiday_calendar(id):
    calendar = HolidayCalendar.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    data = request.get_json()
    
    if 'name' in data: calendar.name = data['name']
    if 'timezone' in data: calendar.timezone = data['timezone']
    if 'weekend_days' in data: calendar.weekend_days_json = json.dumps(data['weekend_days'])
    if 'is_active' in data: calendar.is_active = data['is_active']
    
    db.session.commit()
    return jsonify({'message': 'Holiday calendar updated successfully', 'calendar': serialize(calendar)}), 200

@leave_bp.route('/holidays/calendars/<int:id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR'])
def delete_holiday_calendar(id):
    calendar = HolidayCalendar.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    db.session.delete(calendar)
    db.session.commit()
    return jsonify({'message': 'Holiday calendar deleted successfully'}), 200

@leave_bp.route('/holidays/calendars/<int:id>/holidays', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def add_holiday(id):
    calendar = HolidayCalendar.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    data = request.get_json()
    if not data or 'date' not in data or 'name' not in data:
        return jsonify({'message': 'Missing required fields: date, name'}), 400
    
    holiday_date = parse_date(data['date'])
    if not holiday_date:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    if Holiday.query.filter_by(calendar_id=id, date=holiday_date).first():
        return jsonify({'message': 'Holiday already exists on this date'}), 409

    new_holiday = Holiday(
        calendar_id=id, company_id=g.user.company_id, date=holiday_date,
        name=data['name'], is_optional=data.get('is_optional', False)
    )
    db.session.add(new_holiday)
    db.session.commit()
    return jsonify({'message': 'Holiday added successfully', 'holiday': serialize(new_holiday)}), 201

@leave_bp.route('/holidays/calendars/<int:id>/holidays', methods=['GET'])
@token_required
def list_holidays(id):
    calendar = HolidayCalendar.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    holidays = Holiday.query.filter_by(calendar_id=id).order_by(Holiday.date).all()
    return jsonify([serialize(h) for h in holidays]), 200

@leave_bp.route('/holidays', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_holiday_direct():
    data = request.get_json()
    if not data or 'calendar_id' not in data or 'date' not in data or 'name' not in data:
        return jsonify({'message': 'Missing required fields: calendar_id, date, name'}), 400
    
    calendar = HolidayCalendar.query.filter_by(id=data['calendar_id'], company_id=g.user.company_id).first()
    if not calendar:
        return jsonify({'message': 'Calendar not found'}), 404

    holiday_date = parse_date(data['date'])
    if not holiday_date:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    if Holiday.query.filter_by(calendar_id=data['calendar_id'], date=holiday_date).first():
        return jsonify({'message': 'Holiday already exists on this date'}), 409

    new_holiday = Holiday(
        calendar_id=data['calendar_id'], company_id=g.user.company_id, date=holiday_date,
        name=data['name'], is_optional=data.get('is_optional', False)
    )
    db.session.add(new_holiday)
    db.session.commit()
    return jsonify({'message': 'Holiday added successfully', 'holiday': serialize(new_holiday)}), 201

@leave_bp.route('/holidays', methods=['GET'])
@token_required
def list_all_holidays():
    holidays = Holiday.query.filter_by(company_id=g.user.company_id).order_by(Holiday.date).all()
    return jsonify([serialize(h) for h in holidays]), 200

@leave_bp.route('/holidays/bulk', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_holidays_bulk():
    data = request.get_json()
    if not data or 'calendar_id' not in data or 'holidays' not in data:
        return jsonify({'message': 'Missing required fields: calendar_id, holidays'}), 400
    
    calendar = HolidayCalendar.query.filter_by(id=data['calendar_id'], company_id=g.user.company_id).first()
    if not calendar:
        return jsonify({'message': 'Calendar not found'}), 404

    holidays_list = data['holidays']
    if not isinstance(holidays_list, list):
        return jsonify({'message': 'Holidays must be a list'}), 400

    created_count = 0
    errors = []
    processed_dates = set()

    for index, item in enumerate(holidays_list):
        if 'date' not in item or 'name' not in item:
            errors.append(f"Row {index+1}: Missing date or name")
            continue
        
        h_date = parse_date(item['date'])
        if not h_date:
            errors.append(f"Row {index+1}: Invalid date format")
            continue
        
        if h_date in processed_dates or Holiday.query.filter_by(calendar_id=calendar.id, date=h_date).first():
            errors.append(f"Row {index+1}: Holiday already exists/duplicate date {item['date']}")
            continue

        processed_dates.add(h_date)
        new_holiday = Holiday(
            calendar_id=calendar.id, company_id=g.user.company_id, date=h_date,
            name=item['name'], is_optional=item.get('is_optional', False)
        )
        db.session.add(new_holiday)
        created_count += 1

    if created_count > 0:
        db.session.commit()
    
    return jsonify({
        'message': f'Bulk upload processed. Created: {created_count}, Errors: {len(errors)}',
        'errors': errors
    }), 201

@leave_bp.route('/holidays/assign', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def assign_holiday_calendar():
    data = request.get_json()
    if not data or 'employee_id' not in data or 'calendar_id' not in data:
        return jsonify({'message': 'Missing required fields: employee_id, calendar_id'}), 400

    employee = Employee.query.filter_by(id=data['employee_id'], company_id=g.user.company_id).first()
    if not employee:
        return jsonify({'message': 'Employee not found'}), 404

    calendar = HolidayCalendar.query.filter_by(id=data['calendar_id'], company_id=g.user.company_id).first()
    if not calendar:
        return jsonify({'message': 'Calendar not found'}), 404

    # Remove any existing assignment for this employee to ensure 1:1 relationship
    EmployeeHolidayCalendar.query.filter_by(employee_id=employee.id).delete()

    new_assignment = EmployeeHolidayCalendar(
        company_id=g.user.company_id,
        employee_id=employee.id,
        calendar_id=calendar.id
    )
    db.session.add(new_assignment)
    db.session.commit()

    return jsonify({'message': 'Holiday calendar assigned successfully'}), 200

@leave_bp.route('/holidays/employee/<int:employee_id>', methods=['GET'])
@token_required
def get_employee_holiday_calendar(employee_id):
    employee = Employee.query.filter_by(id=employee_id, company_id=g.user.company_id).first()
    if not employee:
        return jsonify({'message': 'Employee not found'}), 404

    assignment = EmployeeHolidayCalendar.query.filter_by(employee_id=employee.id).first()
    if not assignment:
        return jsonify({'message': 'No holiday calendar assigned'}), 404

    calendar = HolidayCalendar.query.filter_by(id=assignment.calendar_id).first()
    if not calendar:
        return jsonify({'message': 'Calendar not found'}), 404

    holidays = Holiday.query.filter_by(calendar_id=calendar.id).order_by(Holiday.date).all()
    
    result = serialize(calendar)
    result['holidays'] = [serialize(h) for h in holidays]
    return jsonify(result), 200


@leave_bp.route('/balance', methods=['GET'])
@token_required
def get_my_leave_balance():
    # Support Super Admin manual entry
    employee_id = request.args.get('employee_id', type=int)
    
    if g.user.role == 'SUPER_ADMIN' and employee_id:
        emp = Employee.query.get(employee_id)
    else:
        emp = Employee.query.filter_by(user_id=g.user.id).first()
        
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404

    balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()

    result = []
    for b in balances:
        lt = LeaveType.query.get(b.leave_type_id)
        result.append({
            "leave_type_id": b.leave_type_id,
            "leave_type_name": lt.name if lt else None,
            "balance": b.balance,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None
        })

    return jsonify({
        "employee_id": emp.id,
        "company_id": emp.company_id,
        "balances": result
    }), 200

@leave_bp.route('/balance/<int:employee_id>', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employee_leave_balance(employee_id):
    emp = Employee.query.filter_by(id=employee_id, company_id=g.user.company_id).first()
    if not emp:
        return jsonify({'message': 'Employee not found or access denied'}), 404

    balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()

    result = []
    for b in balances:
        lt = LeaveType.query.get(b.leave_type_id)
        result.append({
            "leave_type_id": b.leave_type_id,
            "leave_type_name": lt.name if lt else "Unknown",
            "balance": b.balance,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None
        })

    return jsonify({
        "employee_id": emp.id,
        "company_id": emp.company_id,
        "balances": result
    }), 200

@leave_bp.route('/balance/recompute', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def recompute_balances():
    data = request.get_json()
    if not data or 'employee_id' not in data or 'fiscal_start' not in data or 'fiscal_end' not in data:
        return jsonify({'message': 'Missing required fields: employee_id, fiscal_start, fiscal_end'}), 400

    emp = Employee.query.filter_by(id=data['employee_id'], company_id=g.user.company_id).first()
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404

    fiscal_start = parse_date(data['fiscal_start'])
    fiscal_end = parse_date(data['fiscal_end'])

    if not fiscal_start or not fiscal_end:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    leave_types = LeaveType.query.filter_by(company_id=g.user.company_id, is_active=True).all()
    results = []

    for lt in leave_types:
        mapping = select_policy_mapping(g.user.company_id, emp, lt.id)
        if mapping:
            entitlement = compute_entitlement(g.user.company_id, emp, mapping, fiscal_start, fiscal_end)
            
            bal = LeaveBalance.query.filter_by(employee_id=emp.id, leave_type_id=lt.id).first()
            if not bal:
                bal = LeaveBalance(employee_id=emp.id, leave_type_id=lt.id, balance=0.0)
                db.session.add(bal)
            
            bal.balance = entitlement
            bal.updated_at = datetime.utcnow()
            
            results.append({
                "leave_type": lt.name,
                "allocated": entitlement
            })

    db.session.commit()
    return jsonify({'message': 'Balances recomputed successfully', 'details': results}), 200

@leave_bp.route('/validate', methods=['POST'])
@token_required
def validate_leave():
    data = request.get_json() or {}

    leave_type_id = data.get("leave_type_id")
    from_date = data.get("from_date")
    to_date = data.get("to_date")

    if not leave_type_id or not from_date or not to_date:
        return jsonify({
            "ok": False,
            "message": "leave_type_id, from_date, to_date are required"
        }), 400

    try:
        f = datetime.strptime(from_date, "%Y-%m-%d").date()
        t = datetime.strptime(to_date, "%Y-%m-%d").date()
    except:
        return jsonify({"ok": False, "message": "Date format must be YYYY-MM-DD"}), 400

    if t < f:
        return jsonify({"ok": False, "message": "to_date cannot be less than from_date"}), 400

    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({"ok": False, "message": "Employee profile not found"}), 404

    # Overlap check with existing pending/approved leaves
    overlap = LeaveRequest.query.filter(
        LeaveRequest.employee_id == emp.id,
        LeaveRequest.leave_type_id == leave_type_id,
        LeaveRequest.status.in_(["Pending", "Approved", "Pending Approval"]),
        LeaveRequest.from_date <= t,
        LeaveRequest.to_date >= f
    ).first()

    requested_days = (t - f).days + 1

    if overlap:
        return jsonify({
            "ok": False,
            "message": "Leave overlaps with existing leave",
            "requested_days": requested_days,
            "overlap_leave_id": overlap.id,
            "overlap_from": str(overlap.from_date),
            "overlap_to": str(overlap.to_date),
            "overlap_status": overlap.status
        }), 409

    return jsonify({
        "ok": True,
        "message": "Leave is valid",
        "requested_days": requested_days
    }), 200

@leave_bp.route('/calculate-days', methods=['POST'])
@token_required
def calculate_leave_days():
    data = request.get_json() or {}
    from_date_str = data.get('from_date')
    to_date_str = data.get('to_date')
    is_half_day = data.get('is_half_day', False)
    leave_type_id = data.get('leave_type_id')

    if not from_date_str or not to_date_str or not leave_type_id:
        return jsonify({'message': 'Missing required fields: from_date, to_date, leave_type_id'}), 400

    from_date = parse_date(from_date_str)
    to_date = parse_date(to_date_str)

    if not from_date or not to_date:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    if to_date < from_date:
        return jsonify({'message': 'to_date cannot be earlier than from_date'}), 400

    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404

    mapping = select_policy_mapping(emp.company_id, emp, leave_type_id)
    if not mapping:
        # Default computation if no policy found
        days = (to_date - from_date).days + 1
        if is_half_day:
            days = 0.5 if days == 1 else days - 0.5 # Basic logic
        return jsonify({'requested_days': float(days)}), 200

    from .services import compute_units
    units, meta = compute_units(emp.company_id, emp, mapping, from_date, to_date)
    
    if is_half_day:
        # If it's a single day and half-day, it's 0.5
        # If multiple days, we assume only the last day or some part is half? 
        # Usually "Half Day" toggle in UI means the whole request is for half days or the single day is half.
        # If from_date == to_date and is_half_day, units = 0.5
        if from_date == to_date:
            units = 0.5
        else:
            # If multi-day half-day, it depends on policy, but usually it's used for single day.
            # Let's stick to 0.5 for single day for now as per common HRMS logic.
            units = units - 0.5 if units > 0 else 0

    return jsonify({
        'requested_days': units,
        'meta': meta
    }), 200

@leave_bp.route('/ledger/manual', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def ledger_manual():
    data = request.get_json() or {}

    required = ["employee_id", "leave_type_id", "txn_type", "units"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"message": f"Missing fields: {missing}"}), 400

    # Validate employee belongs to company
    if not Employee.query.filter_by(id=data['employee_id'], company_id=g.user.company_id).first():
        return jsonify({"message": "Employee not found"}), 404

    # Create ledger entry
    entry = LeaveLedger(
        company_id=g.user.company_id,
        employee_id=data["employee_id"],
        leave_type_id=data["leave_type_id"],
        txn_type=data["txn_type"],     # CREDIT/DEBIT
        units=float(data["units"]),
        note=data.get("note", "")
    )
    db.session.add(entry)
    db.session.commit()

    # audit log (optional)
    log_action("LEAVE_LEDGER_MANUAL", "leave_ledger", entry.id, 201, meta=str(data))

    return jsonify({"message": "Ledger entry created", "id": entry.id}), 201

@leave_bp.route('/ledger', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_ledger_history():
    employee_id = request.args.get('employee_id', type=int)
    if not employee_id:
        return jsonify({'message': 'employee_id is a required query parameter'}), 400

    # Validate employee belongs to company
    if not Employee.query.filter_by(id=employee_id, company_id=g.user.company_id).first():
        return jsonify({"message": "Employee not found or access denied"}), 404

    query = LeaveLedger.query.filter_by(company_id=g.user.company_id, employee_id=employee_id)

    leave_type_id = request.args.get('leave_type_id', type=int)
    if leave_type_id:
        query = query.filter_by(leave_type_id=leave_type_id)

    from_date_str = request.args.get('from')
    if from_date_str:
        from_date = parse_date(from_date_str)
        if from_date:
            query = query.filter(LeaveLedger.created_at >= from_date)

    to_date_str = request.args.get('to')
    if to_date_str:
        to_date = parse_date(to_date_str)
        if to_date:
            # To make the 'to' date inclusive, we check for less than the next day's start
            to_datetime = datetime.combine(to_date, datetime.max.time())
            query = query.filter(LeaveLedger.created_at <= to_datetime)

    entries = query.order_by(LeaveLedger.created_at.desc()).all()

    return jsonify([serialize(e) for e in entries]), 200

@leave_bp.route('/encashments', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def list_encashments():
    employee_id = request.args.get('employee_id', type=int)
    leave_type_id = request.args.get('leave_type_id', type=int)
    from_date_str = request.args.get('from')
    to_date_str = request.args.get('to')

    query = LeaveEncashment.query.filter_by(company_id=g.user.company_id)

    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    if leave_type_id:
        query = query.filter_by(leave_type_id=leave_type_id)

    if from_date_str:
        from_date = parse_date(from_date_str)
        if from_date:
            query = query.filter(LeaveEncashment.created_at >= from_date)
    
    if to_date_str:
        to_date = parse_date(to_date_str)
        if to_date:
            to_datetime = datetime.combine(to_date, datetime.max.time())
            query = query.filter(LeaveEncashment.created_at <= to_datetime)

    encashments = query.order_by(LeaveEncashment.created_at.desc()).all()
    return jsonify([serialize(e) for e in encashments]), 200

@leave_bp.route('/encashments', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_encashment():
    data = request.get_json()
    required = ["employee_id", "leave_type_id", "units"]
    if not data or any(k not in data for k in required):
        return jsonify({'message': f'Missing required fields: {required}'}), 400
    
    employee_id = data['employee_id']
    leave_type_id = data['leave_type_id']
    units = float(data['units'])
    note = data.get('note', 'Manual encashment')
    
    emp = Employee.query.filter_by(id=employee_id, company_id=g.user.company_id).first()
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404
        
    if not LeaveType.query.filter_by(id=leave_type_id, company_id=g.user.company_id).first():
        return jsonify({'message': 'Leave type not found'}), 404
        
    if units <= 0:
        return jsonify({'message': 'Units must be a positive number'}), 400
    
    encash(g.user.company_id, employee_id, leave_type_id, units, note)
    db.session.commit()
    log_action("LEAVE_ENCASH_CREATE", "leave_encashment", None, 201, meta=str(data))
    return jsonify({'message': 'Leave encashment processed successfully'}), 201

@leave_bp.route('/encash/manual', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def manual_encashment():
    data = request.get_json()
    required = ["employee_id", "leave_type_id", "units"]
    if not data or any(k not in data for k in required):
        return jsonify({'message': f'Missing required fields: {required}'}), 400
    
    employee_id = data['employee_id']
    leave_type_id = data['leave_type_id']
    units = float(data['units'])
    note = data.get('note', 'Manual encashment by administrator.')
    
    emp = Employee.query.filter_by(id=employee_id, company_id=g.user.company_id).first()
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404
        
    if not LeaveType.query.filter_by(id=leave_type_id, company_id=g.user.company_id).first():
        return jsonify({'message': 'Leave type not found'}), 404
        
    if units <= 0:
        return jsonify({'message': 'Units must be a positive number'}), 400
    
    encash(g.user.company_id, employee_id, leave_type_id, units, note)
    db.session.commit()
    log_action("LEAVE_ENCASH_MANUAL", "leave_encashment", None, 200, meta=str(data))
    return jsonify({'message': 'Leave encashment processed successfully'}), 200

@leave_bp.route('/reports/audit', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_leave_audit_report():
    leave_id = request.args.get('leave_id', type=int)
    if not leave_id:
        return jsonify({'message': 'leave_id is required'}), 400
    
    leave = LeaveRequest.query.filter_by(id=leave_id, company_id=g.user.company_id).first()
    if not leave:
        return jsonify({'message': 'Leave request not found'}), 404

    logs = AuditLog.query.filter_by(
        company_id=g.user.company_id,
        entity='leave_request',
        entity_id=leave_id
    ).order_by(AuditLog.id.desc()).all()
    
    results = []
    for log in logs:
        results.append({
            'id': log.id,
            'action': log.action,
            'user_id': log.user_id,
            'role': log.role,
            'ip_address': log.ip_address,
            'status_code': log.status_code,
            'meta': log.meta,
            'created_at': log.created_at.isoformat() if hasattr(log, 'created_at') and log.created_at else None
        })
    return jsonify(results), 200

@leave_bp.route('/reports/summary', methods=['GET'])
@leave_bp.route('/history', methods=['GET'])
@token_required
def get_leave_summary_report():
    from_date_str = request.args.get('from')
    to_date_str = request.args.get('to')
    company_id = request.args.get('company_id', type=int)
    employee_id = request.args.get('employee_id', type=int)
    
    # Base query
    query = LeaveRequest.query
    
    # Filter by company: 
    # If Super Admin, allow all or specific company.
    # If Admin/HR, restrict to their own company.
    if g.user.role == 'SUPER_ADMIN':
        if company_id:
            query = query.filter(LeaveRequest.company_id == company_id)
    else:
        query = query.filter(LeaveRequest.company_id == g.user.company_id)
        
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    
    if from_date_str:
        from_date = parse_date(from_date_str)
        if from_date:
            query = query.filter(LeaveRequest.to_date >= from_date)
            
    if to_date_str:
        to_date = parse_date(to_date_str)
        if to_date:
            query = query.filter(LeaveRequest.from_date <= to_date)
            
    leaves = query.order_by(LeaveRequest.from_date.desc()).all()
    
    stats = {'Pending': 0, 'Approved': 0, 'Rejected': 0, 'Cancelled': 0}
    details = []
    
    for req in leaves:
        status_key = req.status if req.status in stats else 'Pending'
        if status_key not in stats: stats[status_key] = 0
        stats[status_key] += 1
        
        emp = Employee.query.get(req.employee_id)
        lt = LeaveType.query.get(req.leave_type_id)
        
        approved_by_name = "System"
        if req.approved_by:
            approver = Employee.query.get(req.approved_by)
            if approver:
                approved_by_name = f"{approver.first_name} {approver.last_name}"
        
        details.append({
            'id': req.id,
            'employee_name': f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
            'leave_type': lt.name if lt else "Unknown",
            'leave_type_code': lt.code if lt else "N/A",
            'from_date': req.from_date.isoformat(),
            'to_date': req.to_date.isoformat(),
            'days': (req.to_date - req.from_date).days + 1,
            'status': req.status,
            'approved_by': approved_by_name,
            'applied_on': req.created_at.strftime('%b %d, %Y') if req.created_at else "N/A"
        })
        
    return jsonify({
        'stats': stats,
        'leaves': details
    }), 200

# ==============================================================================
# Existing Leave Application Routes
# ==============================================================================

@leave_bp.route('/mine', methods=['GET'])
@token_required
def get_my_leaves():
    # Support Super Admin manual entry
    employee_id = request.args.get('employee_id', type=int)
    
    if g.user.role == 'SUPER_ADMIN' and employee_id:
        emp = Employee.query.get(employee_id)
    else:
        emp = Employee.query.filter_by(user_id=g.user.id).first()
        
    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404

    query = LeaveRequest.query.filter_by(employee_id=emp.id)

    status = request.args.get('status')
    if status:
        query = query.filter(LeaveRequest.status == status)

    from_date = parse_date(request.args.get('from'))
    if from_date:
        # Find leaves that overlap with the date range, not just fall within it
        query = query.filter(LeaveRequest.to_date >= from_date)

    to_date = parse_date(request.args.get('to'))
    if to_date:
        query = query.filter(LeaveRequest.from_date <= to_date)

    # Join with LeaveType to get the name for a richer response
    leaves_with_type = query.join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)\
        .add_columns(LeaveType.name.label("leave_type_name"))\
        .order_by(LeaveRequest.created_at.desc()).all()
    
    results = []
    for leave_request, leave_type_name in leaves_with_type:
        data = serialize(leave_request)
        data['leave_type_name'] = leave_type_name
        # Add human-readable applied date
        data['applied_on'] = leave_request.created_at.strftime('%b %d, %Y') if leave_request.created_at else "N/A"
        results.append(data)

    # Get current balances
    balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()
    balance_list = []
    for b in balances:
        lt = LeaveType.query.get(b.leave_type_id)
        if lt and lt.is_active:
            balance_list.append({
                "leave_type_id": b.leave_type_id,
                "leave_type_name": lt.name,
                "leave_type_code": lt.code,
                "balance": b.balance
            })

    return jsonify({
        "leaves": results,
        "balances": balance_list
    }), 200

@leave_bp.route('/apply', methods=['POST'])
@token_required
def apply_leave():
    data = request.get_json()
    
    # Support Super Admin manual entry
    if g.user.role == 'SUPER_ADMIN' and data.get('employee_id'):
        emp = Employee.query.get(data['employee_id'])
    else:
        emp = Employee.query.filter_by(user_id=g.user.id).first()

    if not emp:
        return jsonify({'message': 'Employee profile not found'}), 404

    new_leave = LeaveRequest(
        employee_id=emp.id, 
        company_id=data.get('company_id') if g.user.role == 'SUPER_ADMIN' and data.get('company_id') else emp.company_id,
        leave_type_id=data['leave_type_id'],
        from_date=parse_date(data['from_date']), 
        to_date=parse_date(data['to_date']),
        reason=data.get('reason'),
        is_half_day=data.get('is_half_day', False),
        attachment_url=data.get('attachment_url'),
        status=data.get('status', 'Pending')
    )
    db.session.add(new_leave)
    db.session.commit()
    return jsonify({'message': 'Leave application submitted', 'id': new_leave.id}), 201

@leave_bp.route('/<int:id>', methods=['GET', 'PUT'])
@token_required
def manage_leave_request(id):
    leave = LeaveRequest.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    is_owner = emp and leave.employee_id == emp.id

    if request.method == 'GET':
        if not is_owner and g.user.role not in ['ADMIN', 'HR', 'MANAGER']:
            return jsonify({'message': 'Unauthorized'}), 403

        result = serialize(leave)
        lt = LeaveType.query.get(leave.leave_type_id)
        result['leave_type_name'] = lt.name if lt else None
        return jsonify(result), 200

    if request.method == 'PUT':
        if not is_owner:
            return jsonify({'message': 'Unauthorized. Only the owner can edit the request.'}), 403

        if leave.status != 'Pending':
            return jsonify({'message': 'Only pending leave requests can be updated'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is empty'}), 400

        if 'from_date' in data: leave.from_date = parse_date(data['from_date'])
        if 'to_date' in data: leave.to_date = parse_date(data['to_date'])
        if 'reason' in data: leave.reason = data['reason']

        if leave.to_date < leave.from_date:
            return jsonify({'message': 'To date cannot be before from date'}), 400

        db.session.commit()
        
        return jsonify({'message': 'Leave request updated successfully'}), 200

@leave_bp.route('/pending-approvals', methods=['GET'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def get_pending_approvals():
    # Support Super Admin cross-company view
    if g.user.role == 'SUPER_ADMIN' and request.args.get('company_id'):
        query = LeaveRequest.query.filter_by(company_id=request.args.get('company_id'), status='Pending')
    elif g.user.role == 'SUPER_ADMIN':
        query = LeaveRequest.query.filter_by(status='Pending')
    else:
        query = LeaveRequest.query.filter_by(
            company_id=g.user.company_id,
            status='Pending'
        )

    # Join with LeaveType and Employee to get the names for display
    leaves_with_data = query.join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)\
        .join(Employee, LeaveRequest.employee_id == Employee.id)\
        .add_columns(
            LeaveType.name.label("leave_type_name"), 
            Employee.full_name, 
            Employee.department
        )\
        .order_by(LeaveRequest.from_date.asc()).all()
    
    results = []
    for leave_req, leave_type_name, full_name, dept in leaves_with_data:
        data = serialize(leave_req)
        data['leave_type_name'] = leave_type_name
        data['employee_name'] = full_name
        data['dept'] = dept
        data['applied'] = leave_req.created_at.strftime('%b %d, %Y') if leave_req.created_at else "N/A"
        data['days'] = (leave_req.to_date - leave_req.from_date).days + 1 if leave_req.from_date and leave_req.to_date else 0
        results.append(data)

    return jsonify(results), 200

@leave_bp.route('/<int:id>/approve', methods=['POST'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def approve_leave(id):
    leave = LeaveRequest.query.get_or_404(id)
    if g.user.role != 'SUPER_ADMIN' and leave.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
    approver_emp = Employee.query.filter_by(user_id=g.user.id).first()
    data = request.get_json()
    leave.status = data.get('status', 'Approved')
    leave.approved_by = approver_emp.id if approver_emp else None
    db.session.commit()
    return jsonify({'message': f'Leave {leave.status.lower()}'})

@leave_bp.route('/<int:id>/action', methods=['PUT'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def process_leave_action(id):
    leave = LeaveRequest.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    
    data = request.get_json()
    if not data or 'action' not in data:
        return jsonify({'message': 'Missing required field: action'}), 400

    action = data['action'].upper()
    if action not in ['APPROVE', 'REJECT']:
        return jsonify({'message': 'Invalid action. Allowed: APPROVE, REJECT'}), 400

    approver = Employee.query.filter_by(user_id=g.user.id).first()
    leave.status = 'Approved' if action == 'APPROVE' else 'Rejected'
    leave.approved_by = approver.id if approver else None
    
    db.session.commit()
    
    log_action(f"LEAVE_{action}", "leave_request", leave.id, 200, meta=json.dumps(data))
    return jsonify({'message': f'Leave request {leave.status.lower()}'}), 200

@leave_bp.route('/<int:id>/partial-action', methods=['POST'])
@token_required
@role_required(['HR', 'MANAGER', 'ADMIN'])
def partial_leave_action(id):
    leave = LeaveRequest.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()
    
    if leave.status != 'Pending':
        return jsonify({'message': 'Only pending leaves can be processed'}), 400

    approver_emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not approver_emp:
        return jsonify({'message': 'Approver employee profile not found'}), 404
    approver_id = approver_emp.id

    data = request.get_json()
    approved_dates = sorted([parse_date(d) for d in data.get('approved_dates', []) if parse_date(d)])
    rejected_dates = sorted([parse_date(d) for d in data.get('rejected_dates', []) if parse_date(d)])
    comment = data.get('comment', '')

    if not approved_dates and not rejected_dates:
        return jsonify({'message': 'No valid dates provided'}), 400

    # Handle Approved Portion
    if approved_dates:
        # Check contiguity for the main request update
        is_contiguous = all((approved_dates[i+1] - approved_dates[i]).days == 1 for i in range(len(approved_dates)-1))
        if not is_contiguous:
             return jsonify({'message': 'Approved dates must be contiguous for partial approval'}), 400

        leave.from_date = approved_dates[0]
        leave.to_date = approved_dates[-1]
        leave.status = 'Approved'
        leave.approved_by = approver_id
    else:
        # If nothing approved, the whole original request is effectively rejected
        leave.status = 'Rejected'
        leave.approved_by = approver_id

    # Handle Rejected Portion (Create new records for history)
    if rejected_dates:
        # Group contiguous rejected dates into ranges
        ranges = []
        if rejected_dates:
            current_start = rejected_dates[0]
            current_end = rejected_dates[0]
            for i in range(1, len(rejected_dates)):
                if (rejected_dates[i] - rejected_dates[i-1]).days == 1:
                    current_end = rejected_dates[i]
                else:
                    ranges.append((current_start, current_end))
                    current_start = rejected_dates[i]
                    current_end = rejected_dates[i]
            ranges.append((current_start, current_end))
        
        for start, end in ranges:
            new_rej = LeaveRequest(
                company_id=leave.company_id,
                employee_id=leave.employee_id,
                leave_type_id=leave.leave_type_id,
                from_date=start,
                to_date=end,
                reason=f"Partial Rejection (Original #{leave.id}). {comment}",
                status='Rejected',
                approved_by=approver_id
            )
            db.session.add(new_rej)

    db.session.commit()
    return jsonify({'message': 'Partial action processed successfully'}), 200

@leave_bp.route('/<int:id>/timeline', methods=['GET', 'POST'])
@token_required
def get_leave_timeline(id):
    # Ledger entries related to this request
    ledger_entries = LeaveLedger.query.filter_by(request_id=id).order_by(LeaveLedger.created_at.asc()).all()
    return jsonify([serialize(entry) for entry in ledger_entries]), 200

@leave_bp.route('/year-end/process', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def process_year_end():
    data = request.get_json()
    policy_id = data.get('policy_id')
    fiscal_end_str = data.get('fiscal_year_end')
    
    if not policy_id or not fiscal_end_str:
        return jsonify({'message': 'Missing policy_id or fiscal_year_end'}), 400

    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    leave_types = LeaveType.query.filter_by(company_id=g.user.company_id).all()
    results = []
    
    for emp in employees:
        for lt in leave_types:
            mapping = select_policy_mapping(g.user.company_id, emp, lt.id)
            if mapping and mapping.policy_id == policy_id:
                bal = LeaveBalance.query.filter_by(employee_id=emp.id, leave_type_id=lt.id).first()
                if not bal or bal.balance <= 0:
                    continue

                cf = min(bal.balance, mapping.carry_forward_limit or 0)
                remainder = bal.balance - cf
                encash = min(remainder, mapping.encashment_limit or 0)
                lapse = remainder - encash

                if lapse > 0:
                    add_ledger(g.user.company_id, emp.id, lt.id, 'LAPSE', lapse, f"Year End {fiscal_end_str}")
                if encash > 0:
                    add_ledger(g.user.company_id, emp.id, lt.id, 'ENCASH', encash, f"Year End {fiscal_end_str}")
                    db.session.add(LeaveEncashment(company_id=g.user.company_id, employee_id=emp.id, leave_type_id=lt.id, units=encash, note=f"Year End {fiscal_end_str}"))
                
                bal.balance = cf
                bal.updated_at = datetime.utcnow()
                results.append({"employee_id": emp.id, "leave_type": lt.code, "carried_forward": cf, "encashed": encash, "lapsed": lapse})

    db.session.commit()
    return jsonify({'message': 'Year end processing complete', 'details': results}), 200

@leave_bp.route('/<int:id>/cancel', methods=['POST'])
@token_required
def cancel_leave_request(id):
    leave = LeaveRequest.query.filter_by(id=id, company_id=g.user.company_id).first_or_404()

    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not (emp and leave.employee_id == emp.id):
        return jsonify({'message': 'Unauthorized'}), 403

    if leave.status != 'Pending':
        return jsonify({'message': 'Only pending leaves can be cancelled'}), 400

    leave.status = 'Cancelled'
    db.session.commit()
    return jsonify({'message': 'Leave request cancelled'}), 200