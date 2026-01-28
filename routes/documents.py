import os
from flask import Blueprint, request, jsonify, send_file, current_app, g
from werkzeug.utils import secure_filename
from models import db
from models.employee_documents import EmployeeDocument
from models.employee import Employee
from utils.decorators import token_required, role_required
import uuid
from datetime import datetime

documents_bp = Blueprint('documents', __name__)

def get_upload_folder():
    upload_folder = os.path.join(current_app.root_path, 'uploads', 'documents')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

@documents_bp.route('/upload', methods=['POST'])
@token_required
@role_required(['EMPLOYEE'])
def upload_document():
    current_user = g.user
    file = request.files.get("file")
    document_type = request.form.get("document_type")

    if not file or not document_type:
        return jsonify({"error": "File and document type required"}), 400

    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # Generate unique filename
    unique_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    
    upload_folder = get_upload_folder()
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Get file size
    file_size = os.path.getsize(file_path)

    emp = Employee.query.filter_by(user_id=current_user.id).first()
    if not emp:
        return jsonify({"message": "Employee profile not found"}), 404

    new_document = EmployeeDocument(
        employee_id=emp.id,
        company_id=current_user.company_id,
        document_type=document_type,
        file_name=filename,
        file_path=file_path,
        file_type=file_ext,
        file_size=file_size,
        status="PENDING"
    )

    db.session.add(new_document)
    db.session.commit()
    
    return jsonify({
        "message": "Document uploaded successfully",
        "status": "PENDING"
    }), 201

@documents_bp.route("/pending", methods=["GET"])
@token_required
@role_required(["ADMIN", "HR"])
def pending_documents():
    # Filter by company
    docs = EmployeeDocument.query.filter_by(
        company_id=g.user.company_id, 
        status="PENDING",
        is_active=True
    ).all()

    return jsonify([
        {
            "id": d.id,
            "employee_id": d.employee_id,
            "document_type": d.document_type,
            "file_name": d.file_name,
            "uploaded_at": d.uploaded_at,
            "status": d.status
        } for d in docs
    ])

@documents_bp.route("/approve/<int:doc_id>", methods=["PUT"])
@token_required
@role_required(["ADMIN", "HR"])
def approve_document(doc_id):
    doc = EmployeeDocument.query.get_or_404(doc_id)
    
    # Security check: Ensure doc belongs to same company
    if doc.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403

    doc.status = "APPROVED"
    doc.approved_by = g.user.id
    doc.approved_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Document approved"}), 200

@documents_bp.route("/reject/<int:doc_id>", methods=["PUT"])
@token_required
@role_required(["ADMIN", "HR"])
def reject_document(doc_id):
    data = request.get_json(force=True)
    doc = EmployeeDocument.query.get_or_404(doc_id)
    
    if doc.company_id != g.user.company_id:
        return jsonify({"message": "Unauthorized"}), 403

    doc.status = "REJECTED"
    doc.remarks = data.get("remarks")

    db.session.commit()
    return jsonify({"message": "Document rejected"}), 200

@documents_bp.route("/my-documents", methods=["GET"])
@token_required
@role_required(["EMPLOYEE"])
def my_documents():
    docs = EmployeeDocument.query.filter_by(
        employee_id=g.user.id,
        is_active=True
    ).all()

    return jsonify([
        {
            "document_type": d.document_type,
            "file_name": d.file_name,
            "status": d.status,
            "remarks": d.remarks,
            "uploaded_at": d.uploaded_at
        } for d in docs
    ])

@documents_bp.route('/download/<filename>')
@token_required
def download_document(filename):
    # Find document by filename (assuming filename is unique in path or we search by file_path logic)
    # Since we store full path, we might need to query by file_path containing filename
    # For simplicity, let's assume we query by the stored file_name or we need to adjust the query.
    # Better approach: Query by ID for download, but keeping filename route for now:
    
    document = EmployeeDocument.query.filter(EmployeeDocument.file_path.contains(filename)).first_or_404()
    
    # Permission check
    if document.employee_id != g.user.id and g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
        return jsonify({'message': 'Access denied'}), 403
        
    return send_file(document.file_path, as_attachment=True)