from flask import Blueprint, jsonify, request, g
from datetime import datetime
from models import db
from models.user import User
from models.employee import Employee
from models.employee_documents import EmployeeDocument
from models.department import Department
from models.designation import Designation
from models.hr_documents import LetterTemplate, LetterRequest
from utils.decorators import token_required, role_required
from utils.audit_logger import log_action
from werkzeug.security import generate_password_hash

onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/stats', methods=['GET'])
@token_required
@role_required(['HR'])
def get_onboarding_stats():
    # Total Hires (Employees with onboarding_status not Completed? or all?)
    # For now, let's assume all employees in the onboarding system
    all_onboarding = Employee.query.filter(Employee.company_id == g.user.company_id, Employee.onboarding_status != None).all()
    
    total_hires = len(all_onboarding)
    docs_pending = 0
    in_progress = 0
    verified = 0

    for emp in all_onboarding:
        if emp.onboarding_status == 'Pending':
            docs_pending += 1
        elif emp.onboarding_status == 'In Progress' or emp.onboarding_status == 'Document Verification':
            in_progress += 1
        elif emp.onboarding_status == 'Completed':
            verified += 1
            
    return jsonify({
        'success': True,
        'data': {
            'total_hires': total_hires,
            'docs_pending': docs_pending,
            'in_progress': in_progress,
            'verified': verified
        }
    }), 200

@onboarding_bp.route('/form-options', methods=['GET'])
@token_required
@role_required(['HR'])
def get_form_options():
    departments = Department.query.filter_by(company_id=g.user.company_id, is_active=True).all()
    designations = Designation.query.filter_by(company_id=g.user.company_id).all()
    
    # Static list based on user image
    employment_types = ['Fulltime', 'Intern', 'Contract']
    
    return jsonify({
        'success': True,
        'data': {
            'departments': [{'id': d.id, 'name': d.department_name} for d in departments],
            'designations': [{'id': d.id, 'name': d.designation_name} for d in designations],
            'employment_types': employment_types
        }
    }), 200

@onboarding_bp.route('/candidates', methods=['GET'])
@token_required
@role_required(['HR'])
def get_candidates():
    candidates = Employee.query.filter(Employee.company_id == g.user.company_id, Employee.onboarding_status != None).all()
    
    output = []
    for emp in candidates:
        # Calculate submission percentage
        docs = EmployeeDocument.query.filter_by(employee_id=emp.id).all()
        total_docs = len(docs)
        verified_docs = len([d for d in docs if d.verified])
        submission_pct = (verified_docs / total_docs * 100) if total_docs > 0 else 0
        
        output.append({
            'id': emp.id,
            'full_name': emp.full_name,
            'department': emp.department,
            'joining_date': emp.date_of_joining.strftime('%Y-%m-%d') if emp.date_of_joining else None,
            'status': emp.onboarding_status,
            'submission_pct': round(submission_pct),
            'avatar_url': f"https://ui-avatars.com/api/?name={emp.full_name}&background=random" # Placeholder
        })
        
    return jsonify({'success': True, 'data': output}), 200

@onboarding_bp.route('/<int:employee_id>/checklist', methods=['GET'])
@token_required
@role_required(['HR'])
def get_checklist(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    if emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    docs = EmployeeDocument.query.filter_by(employee_id=employee_id).all()
    
    educational = []
    id_proofs = []
    
    educational_types = ['10th Certificate', 'Inter Certificate', 'Degree Certificate', 'PG Certificate']
    id_proof_types = ['PAN Card', 'Aadhaar Card', 'Passport']
    
    # Organize documents into categories
    for doc in docs:
        doc_data = {
            'id': doc.id,
            'name': doc.document_type,
            'status': 'Verified' if doc.verified else 'Pending',
            'updated_at': doc.updated_at.strftime('%b %d') if doc.updated_at else None,
            'file_url': doc.file_url
        }
        if doc.document_type in educational_types:
            educational.append(doc_data)
        elif doc.document_type in id_proof_types:
            id_proofs.append(doc_data)
            
    return jsonify({
        'success': True,
        'data': {
            'employee_name': emp.full_name,
            'educational_certificates': educational,
            'id_proofs': id_proofs
        }
    }), 200

@onboarding_bp.route('/<int:employee_id>/letter-options', methods=['GET'])
@token_required
@role_required(['HR'])
def get_letter_options(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    if emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    templates = LetterTemplate.query.filter_by(company_id=g.user.company_id, is_active=True).all()
    
    # Based on user image
    letter_types = ['Offer Letter', 'Appointment Letter', 'Increment Letter', 'Relieving Letter']
    template_options = ['Standard Format', 'Modern Format', 'Professional Format']
    
    return jsonify({
        'success': True,
        'data': {
            'candidate_name': emp.full_name,
            'candidate_email': emp.personal_email,
            'letter_types': letter_types,
            'template_options': template_options,
            'default_date': datetime.utcnow().strftime('%Y-%m-%d')
        }
    }), 200

@onboarding_bp.route('/<int:employee_id>/generate-letter', methods=['POST'])
@token_required
@role_required(['HR'])
def generate_onboarding_letter(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    if emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    
    # Required fields from modal
    required = ['letter_type', 'date', 'template_option']
    for field in required:
        if field not in data:
            return jsonify({'message': f'Missing field: {field}'}), 400
            
    # Create Letter Request
    new_letter = LetterRequest(
        company_id=g.user.company_id,
        employee_id=emp.id,
        employee_name=emp.full_name,
        employee_email=emp.personal_email,
        letter_type=data['letter_type'],
        letter_date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
        template_option=data['template_option'],
        send_email_copy=data.get('send_email_copy', False),
        status='GENERATED',
        created_by=g.user.id
    )
    
    db.session.add(new_letter)
    db.session.commit()
    
    log_action("GENERATE_ONBOARDING_LETTER", "LetterRequest", new_letter.id, meta={"type": data['letter_type']})
    
    return jsonify({
        'success': True,
        'message': 'Letter generated successfully',
        'data': {
            'letter_id': new_letter.id,
            'status': new_letter.status
        }
    }), 201

@onboarding_bp.route('/<int:employee_id>/verify-document/<int:document_id>', methods=['POST'])
@token_required
@role_required(['HR'])
def verify_document(employee_id, document_id):
    doc = EmployeeDocument.query.get_or_404(document_id)
    if doc.employee_id != employee_id:
        return jsonify({'message': 'Invalid document for employee'}), 400
        
    emp = Employee.query.get(employee_id)
    if emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    doc.verified = True
    doc.verified_by = g.user.id
    doc.verified_date = datetime.utcnow()
    
    # Update employee onboarding status if all docs verified
    all_docs = EmployeeDocument.query.filter_by(employee_id=employee_id).all()
    if all(d.verified for d in all_docs):
        emp.onboarding_status = 'Completed'
        emp.onboarding_completed_at = datetime.utcnow()
    else:
        emp.onboarding_status = 'Document Verification'
        
    db.session.commit()
    
    log_action("VERIFY_DOCUMENT", "EmployeeDocument", document_id, meta={"onboarding_status": emp.onboarding_status})
    
    return jsonify({
        'success': True,
        'message': 'Document verified successfully', 
        'data': {'onboarding_status': emp.onboarding_status}
    }), 200

@onboarding_bp.route('/<int:employee_id>/verify-all', methods=['POST'])
@token_required
@role_required(['HR'])
def verify_all_documents(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    if emp.company_id != g.user.company_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    docs = EmployeeDocument.query.filter_by(employee_id=employee_id).all()
    for doc in docs:
        doc.verified = True
        doc.verified_by = g.user.id
        doc.verified_date = datetime.utcnow()
        
    emp.onboarding_status = 'Completed'
    emp.onboarding_completed_at = datetime.utcnow()
    
    db.session.commit()
    
    log_action("VERIFY_ALL_DOCUMENTS", "Employee", employee_id)
    
    return jsonify({'success': True, 'message': 'All documents verified successfully'}), 200

@onboarding_bp.route('/add-candidate', methods=['POST'])
@token_required
@role_required(['HR'])
def add_candidate():
    data = request.get_json()
    
    # Required fields
    required = ['full_name', 'personal_email', 'department', 'designation', 'date_of_joining', 'employment_type']
    for field in required:
        if field not in data:
            return jsonify({'message': f'Missing field: {field}'}), 400
            
    # Split full name
    name_parts = data['full_name'].split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Create User
    import secrets
    temp_password = secrets.token_hex(8)
    
    user = User(
        email=data['personal_email'],
        username=f"{first_name.lower()}.{last_name.lower() or 'emp'}",
        password=generate_password_hash(temp_password),
        role='EMPLOYEE',
        company_id=g.user.company_id,
        status='INACTIVE'
    )
    db.session.add(user)
    db.session.flush()
    
    # Create Employee
    emp = Employee(
        user_id=user.id,
        company_id=g.user.company_id,
        full_name=data['full_name'],
        personal_email=data['personal_email'],
        phone_number=data.get('phone_number'),
        department=data['department'],
        designation=data['designation'],
        employment_type=data['employment_type'],
        date_of_joining=datetime.strptime(data['date_of_joining'], '%Y-%m-%d').date(),
        onboarding_status='Pending'
    )
    db.session.add(emp)
    
    # Add default document placeholders as shown in image
    default_docs = [
        '10th Certificate', 'Inter Certificate', 'Degree Certificate', 'PG Certificate',
        'PAN Card', 'Aadhaar Card', 'Passport'
    ]
    for doc_type in default_docs:
        doc = EmployeeDocument(
            employee_id=emp.id,
            document_type=doc_type,
            verified=False
        )
        db.session.add(doc)
        
    db.session.commit()
    
    log_action("ADD_CANDIDATE", "Employee", emp.id, meta={"name": data['full_name']})
    
    return jsonify({
        'success': True,
        'message': 'Candidate added to onboarding', 
        'data': {'employee_id': emp.id}
    }), 201
