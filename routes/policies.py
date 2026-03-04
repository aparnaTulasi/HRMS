from flask import Blueprint, request, jsonify, send_from_directory, current_app, g
from models import db
from models.policy import Policy, PolicyCategory, PolicyAcknowledgment, PolicyViolation, PolicyException
from models.user import User
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from utils.decorators import token_required

policies_bp = Blueprint('policies', __name__)

# Helper for role check
def is_admin_or_hr():
    return g.user.role in ['ADMIN', 'HR', 'SUPER_ADMIN', 'MANAGER']

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'policies')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@policies_bp.route('/categories', methods=['GET'])
@token_required
def get_categories():
    categories = PolicyCategory.query.all()
    return jsonify([c.to_dict() for c in categories])

@policies_bp.route('/categories', methods=['POST'])
@token_required
def create_category():
    if not is_admin_or_hr():
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json(force=True)
    category = PolicyCategory(name=data['name'], description=data.get('description'))
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201

@policies_bp.route('/', methods=['GET'])
@token_required
def get_policies():
    policies = Policy.query.all()
    return jsonify([p.to_dict() for p in policies])

@policies_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_policy(id):
    policy = Policy.query.get_or_404(id)
    return jsonify(policy.to_dict())

@policies_bp.route('/', methods=['POST'])
@token_required
def create_policy():
    if not is_admin_or_hr():
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json(force=True)
    policy = Policy(
        title=data['title'],
        description=data.get('description'),
        category_id=data['category_id'],
        effective_date=datetime.strptime(data['effective_date'], '%Y-%m-%d').date()
    )
    db.session.add(policy)
    db.session.commit()
    return jsonify(policy.to_dict()), 201

@policies_bp.route('/<int:id>/acknowledge', methods=['POST'])
@token_required
def acknowledge_policy(id):
    exists = PolicyAcknowledgment.query.filter_by(policy_id=id, user_id=g.user.id).first()
    if exists:
        return jsonify({'message': 'Already acknowledged'}), 200
    
    ack = PolicyAcknowledgment(policy_id=id, user_id=g.user.id)
    db.session.add(ack)
    db.session.commit()
    return jsonify({'message': 'Policy acknowledged'}), 201

@policies_bp.route('/acknowledgments', methods=['GET'])
@token_required
def get_acknowledgments():
    if is_admin_or_hr():
        acks = PolicyAcknowledgment.query.all()
    else:
        acks = PolicyAcknowledgment.query.filter_by(user_id=g.user.id).all()
    
    results = [{
        'id': ack.id,
        'policy_id': ack.policy_id,
        'user_id': ack.user_id,
        'acknowledged_at': ack.acknowledged_at.isoformat()
    } for ack in acks]
    return jsonify(results)

@policies_bp.route('/violations', methods=['GET'])
@token_required
def get_violations():
    if is_admin_or_hr():
        violations = PolicyViolation.query.all()
    else:
        violations = PolicyViolation.query.filter_by(user_id=g.user.id).all()
    
    results = [{
        'id': v.id,
        'policy_id': v.policy_id,
        'description': v.description,
        'status': v.status,
        'reported_at': v.reported_at.isoformat()
    } for v in violations]
    return jsonify(results)

@policies_bp.route('/violations', methods=['POST'])
@token_required
def report_violation():
    data = request.get_json(force=True)
    # Default to current user if offender not specified (self-report or test)
    offender_id = data.get('user_id', g.user.id)
    
    violation = PolicyViolation(
        policy_id=data['policy_id'],
        user_id=offender_id,
        reported_by_id=g.user.id,
        description=data['description']
    )
    db.session.add(violation)
    db.session.commit()
    return jsonify({'message': 'Violation reported', 'id': violation.id}), 201

@policies_bp.route('/violations/<int:id>/approve', methods=['POST'])
@token_required
def approve_violation(id):
    if not is_admin_or_hr():
        return jsonify({'error': 'Unauthorized'}), 403
    
    violation = PolicyViolation.query.get_or_404(id)
    violation.status = 'CLOSED'
    db.session.commit()
    return jsonify({'message': 'Violation approved/closed'})

@policies_bp.route('/exceptions', methods=['POST'])
@token_required
def request_exception():
    data = request.get_json(force=True)
    ex = PolicyException(
        policy_id=data['policy_id'],
        user_id=g.user.id,
        reason=data['reason']
    )
    db.session.add(ex)
    db.session.commit()
    return jsonify({'message': 'Exception requested', 'id': ex.id}), 201

@policies_bp.route('/exceptions/<int:id>/approve', methods=['POST'])
@token_required
def approve_exception(id):
    if not is_admin_or_hr():
        return jsonify({'error': 'Unauthorized'}), 403
    ex = PolicyException.query.get_or_404(id)
    ex.status = 'APPROVED'
    ex.approved_by_id = g.user.id
    ex.reviewed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Exception approved'})

@policies_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard():
    return jsonify({
        'total_policies': Policy.query.count(),
        'my_acknowledgments': PolicyAcknowledgment.query.filter_by(user_id=g.user.id).count(),
        'pending_violations': PolicyViolation.query.filter_by(user_id=g.user.id, status='OPEN').count()
    })

@policies_bp.route('/<int:id>/upload', methods=['POST'])
@token_required
def upload_document(id):
    if not is_admin_or_hr():
        return jsonify({'error': 'Unauthorized'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        policy = Policy.query.get_or_404(id)
        policy.document_url = filename
        db.session.commit()
        return jsonify({'message': 'File uploaded', 'url': filename})
    return jsonify({'error': 'Invalid file'}), 400

@policies_bp.route('/documents/<path:filename>', methods=['GET'])
def download_document(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@policies_bp.route('/compliance-report', methods=['GET'])
@token_required
def compliance_report():
    if not is_admin_or_hr():
        return jsonify({'error': 'Unauthorized'}), 403
    
    total_users = User.query.count()
    policies = Policy.query.filter_by(is_active=True).all()
    
    report = []
    for policy in policies:
        ack_count = PolicyAcknowledgment.query.filter_by(policy_id=policy.id).count()
        compliance_percentage = (ack_count / total_users * 100) if total_users > 0 else 0
        
        report.append({
            'policy_id': policy.id,
            'title': policy.title,
            'total_users': total_users,
            'acknowledged_count': ack_count,
            'compliance_percentage': round(compliance_percentage, 2)
        })
    
    return jsonify(report)