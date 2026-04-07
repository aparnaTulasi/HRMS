import io
from flask import Blueprint, request, jsonify, g, current_app, send_file
from werkzeug.utils import secure_filename
from models import db
from models.employee_documents import EmployeeDocument
from models.hr_documents import HRDocument
from models.employee import Employee
from models.notification import Notification
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from datetime import datetime

doc_center_bp = Blueprint('document_center', __name__)

# --- Employee Endpoints ---

@doc_center_bp.route('/policies', methods=['GET'])
@token_required
def get_company_policies():
    """
    Lists non-sensitive company policies for employees to view/download.
    """
    cid = g.user.company_id
    policies = HRDocument.query.filter_by(
        company_id=cid, 
        is_sensitive=False, 
        is_active=True
    ).with_entities(HRDocument.id, HRDocument.title, HRDocument.category, HRDocument.file_type, HRDocument.file_size, HRDocument.created_at).all()
    
    output = []
    for p in policies:
        output.append({
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "type": p.file_type or "PDF",
            "size": p.file_size or "---",
            "date": p.created_at.strftime("%b %d, %Y"),
            "download_url": f"/api/document-center/download/{p.id}?type=policy"
        })
    return jsonify({"success": True, "data": output}), 200

@doc_center_bp.route('/my-documents', methods=['GET'])
@token_required
def get_my_documents():
    """
    Lists documents uploaded by or for the current employee.
    """
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile required"}), 400
        
    docs = EmployeeDocument.query.filter_by(employee_id=emp_id, is_active=True)\
                               .with_entities(EmployeeDocument.id, EmployeeDocument.document_name, EmployeeDocument.document_type, EmployeeDocument.verification_status, EmployeeDocument.created_at).all()
    output = []
    for d in docs:
        output.append({
            "id": d.id,
            "name": d.document_name,
            "type": d.document_type,
            "status": d.verification_status,
            "date": d.created_at.strftime("%b %d, %Y"),
            "download_url": f"/api/document-center/download/{d.id}?type=employee"
        })
    return jsonify({"success": True, "data": output}), 200

@doc_center_bp.route('/upload', methods=['POST'])
@token_required
def employee_upload():
    """
    Allows an employee to upload their own personal documents directly into the DB.
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
        
    file = request.files['file']
    doc_type = request.form.get('document_type', 'Other')
    emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    
    if not emp_id:
        return jsonify({"success": False, "message": "Employee profile required"}), 400

    filename = secure_filename(file.filename)
    file_data = file.read() # Reading binary content
    
    new_doc = EmployeeDocument(
        employee_id=emp_id,
        document_type=doc_type,
        document_name=filename,
        file_content=file_data, # Directly saved in DB as BLOB
        verification_status='PENDING VERIFICATION',
        uploaded_by_role='EMPLOYEE'
    )
    db.session.add(new_doc)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Document uploaded successfully to database"}), 201

# --- Admin/Manager Endpoints (Hierarchical Access) ---

@doc_center_bp.route('/admin/list', methods=['GET'])
@token_required
def admin_list_documents():
    """
    Hierarchical list for Management.
    User's own documents are EXCLUDED from this list as they must manage them via the Employee view.
    """
    role = g.user.role
    cid = g.user.company_id
    current_emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    
    q = EmployeeDocument.query.join(Employee, Employee.id == EmployeeDocument.employee_id)\
                             .filter(Employee.company_id == cid, EmployeeDocument.is_active == True)
    
    # "Not their data" rule: Filter out current user's documents
    if current_emp_id:
        q = q.filter(EmployeeDocument.employee_id != current_emp_id)
    
    if role == 'SUPER_ADMIN':
        pass 
    elif role == 'ADMIN':
        q = q.filter(EmployeeDocument.uploaded_by_role.in_(['HR', 'EMPLOYEE']))
    elif role == 'HR':
        q = q.filter(EmployeeDocument.uploaded_by_role == 'EMPLOYEE')
    else:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    docs = q.all()
    output = []
    for d in docs:
        output.append({
            "id": d.id,
            "employee_name": d.employee.full_name if d.employee else "N/A",
            "document_name": d.document_name,
            "document_type": d.document_type,
            "verification_status": d.verification_status,
            "uploaded_by_role": d.uploaded_by_role,
            "date": d.created_at.strftime("%b %d, %Y")
        })
    return jsonify({"success": True, "data": output}), 200

@doc_center_bp.route('/admin/update/<int:doc_id>', methods=['PUT', 'POST'])
@token_required
def admin_update_document(doc_id):
    """
    CRUD: Edit employee document metadata AND optionally replace the file BLOB.
    """
    doc = EmployeeDocument.query.get_or_404(doc_id)
    
    # Self-management check
    if g.user.employee_profile and doc.employee_id == g.user.employee_profile.id:
        return jsonify({"success": False, "message": "Please use the Employee view to update your own documents"}), 403
        
    if g.user.role == 'HR' and doc.uploaded_by_role != 'EMPLOYEE':
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    data = request.get_json() if request.is_json else request.form
    doc.document_name = data.get('document_name', doc.document_name)
    doc.document_type = data.get('document_type', doc.document_type)
    
    # Optional File Replacement
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            doc.file_content = file.read()
            doc.document_name = secure_filename(file.filename)
            
    db.session.commit()
    return jsonify({"success": True, "message": "Document updated successfully"}), 200

@doc_center_bp.route('/admin/delete/<int:doc_id>', methods=['DELETE'])
@token_required
def admin_delete_document(doc_id):
    """
    CRUD: Delete document from DB.
    """
    doc = EmployeeDocument.query.get_or_404(doc_id)
    if g.user.employee_profile and doc.employee_id == g.user.employee_profile.id:
        return jsonify({"success": False, "message": "Use Employee view for your own docs"}), 403
        
    if g.user.role == 'HR' and doc.uploaded_by_role != 'EMPLOYEE':
        return jsonify({"success": False, "message": "Access denied"}), 403

    db.session.delete(doc)
    db.session.commit()
    return jsonify({"success": True, "message": "Document removed from database"}), 200

@doc_center_bp.route('/admin/verify/<int:doc_id>', methods=['POST'])
@token_required
def admin_verify_document(doc_id):
    """
    Verifies a document and sends a notification.
    """
    data = request.get_json()
    status = data.get('status')
    notes = data.get('notes', "")
    doc = EmployeeDocument.query.get_or_404(doc_id)
    
    if g.user.employee_profile and doc.employee_id == g.user.employee_profile.id:
        return jsonify({"success": False, "message": "You cannot verify your own docs"}), 403
        
    doc.verification_status = status
    doc.notes = notes
    doc.verified_by = g.user.id
    doc.verified_date = datetime.utcnow()
    
    message = f"Your document '{doc.document_name}' has been {status} by {g.user.role}."
    notif = Notification(user_id=doc.employee.user_id if doc.employee else None, message=message)
    db.session.add(notif)
    db.session.commit()
    return jsonify({"success": True, "message": f"Document {status.lower()} successfully"}), 200

@doc_center_bp.route('/admin/upload', methods=['POST'])
@token_required
def admin_upload_for_employee():
    """
    Allows HR/Admin/Super Admin to upload a document for another employee.
    """
    if g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    target_emp_id = request.form.get('employee_id')
    current_emp_id = g.user.employee_profile.id if g.user.employee_profile else None
    if not target_emp_id or (current_emp_id and int(target_emp_id) == current_emp_id):
        return jsonify({"success": False, "message": "Invalid target employee"}), 400

    file = request.files['file']
    doc_type = request.form.get('document_type', 'Other')
    file_data = file.read()
    
    new_doc = EmployeeDocument(
        employee_id=int(target_emp_id),
        document_type=doc_type,
        document_name=secure_filename(file.filename),
        file_content=file_data,
        verification_status='VERIFIED',
        uploaded_by_role=g.user.role
    )
    db.session.add(new_doc)
    db.session.commit()
    return jsonify({"success": True, "message": "Document uploaded for employee"}), 201

# --- Management CRUD for Company Policies ---

@doc_center_bp.route('/policies/upload', methods=['POST'])
@token_required
def admin_upload_policy():
    """
    Allows HR/Admin/Super Admin to upload a new Company Policy.
    """
    if g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    file = request.files['file']
    title = request.form.get('title')
    category = request.form.get('category', 'Policy')
    is_sensitive = request.form.get('is_sensitive', 'false').lower() == 'true'
    
    file_data = file.read()
    new_policy = HRDocument(
        company_id=g.user.company_id,
        title=title or secure_filename(file.filename),
        category=category,
        file_content=file_data,
        file_type=secure_filename(file.filename).rsplit('.', 1)[1].upper() if '.' in file.filename else 'PDF',
        file_size=f"{len(file_data) / (1024*1024):.1f} MB",
        is_sensitive=is_sensitive,
        created_by=g.user.id
    )
    db.session.add(new_policy)
    db.session.commit()
    return jsonify({"success": True, "message": "Policy uploaded successfully"}), 201

@doc_center_bp.route('/policies/update/<int:policy_id>', methods=['PUT', 'POST'])
@token_required
def admin_update_policy(policy_id):
    """
    Allows HR/Admin/Super Admin to edit policy metadata AND replace the file BLOB.
    """
    if g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    policy = HRDocument.query.get_or_404(policy_id)
    data = request.get_json() if request.is_json else request.form
    
    policy.title = data.get('title', policy.title)
    policy.category = data.get('category', policy.category)
    policy.is_sensitive = str(data.get('is_sensitive', policy.is_sensitive)).lower() == 'true'
    policy.status = data.get('status', policy.status)
    
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            file_data = file.read()
            policy.file_content = file_data
            policy.file_type = secure_filename(file.filename).rsplit('.', 1)[1].upper() if '.' in file.filename else 'PDF'
            policy.file_size = f"{len(file_data) / (1024*1024):.1f} MB"
    
    db.session.commit()
    return jsonify({"success": True, "message": "Policy updated successfully"}), 200

@doc_center_bp.route('/policies/delete/<int:policy_id>', methods=['DELETE'])
@token_required
def admin_delete_policy(policy_id):
    """
    Allows HR/Admin/Super Admin to delete a Company Policy.
    """
    if g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    policy = HRDocument.query.get_or_404(policy_id)
    db.session.delete(policy)
    db.session.commit()
    return jsonify({"success": True, "message": "Policy deleted permanently"}), 200

@doc_center_bp.route('/policies/admin-list', methods=['GET'])
@token_required
def admin_list_policies():
    """
    Full list of policies for Management.
    """
    if g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    policies = HRDocument.query.filter_by(company_id=g.user.company_id).all()
    output = []
    for p in policies:
        output.append({
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "status": p.status,
            "is_sensitive": p.is_sensitive,
            "date": p.created_at.strftime("%Y-%m-%d")
        })
    return jsonify({"success": True, "data": output}), 200

@doc_center_bp.route('/download/<int:doc_id>', methods=['GET'])
@token_required
def download_any_document(doc_id):
    """
    Centralized download handler: Retrieves BLOB from database.
    """
    doc_type = request.args.get('type')
    if doc_type == 'policy':
        doc = HRDocument.query.get_or_404(doc_id)
        if doc.is_sensitive and g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
            return jsonify({"message": "Access denied"}), 403
        content, name = doc.file_content, doc.title
    else:
        doc = EmployeeDocument.query.get_or_404(doc_id)
        current_emp_id = g.user.employee_profile.id if g.user.employee_profile else None
        if doc.employee_id != current_emp_id and g.user.role not in ['HR', 'ADMIN', 'SUPER_ADMIN']:
            return jsonify({"message": "Access denied"}), 403
        content, name = doc.file_content, doc.document_name
            
    if not content:
        return jsonify({"success": False, "message": "No file in DB"}), 404
        
    return send_file(io.BytesIO(content), as_attachment=True, download_name=name)
