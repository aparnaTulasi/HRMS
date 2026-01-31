import os
from flask import Blueprint, request, jsonify, send_file, current_app, g
from werkzeug.utils import secure_filename
from models import db
from models.employee_documents import EmployeeDocument, DocumentType
from models.employee import Employee
from utils.decorators import token_required
import uuid
from datetime import datetime

documents_bp = Blueprint('documents', __name__)

def get_upload_folder():
    upload_folder = os.path.join(current_app.root_path, 'uploads', 'documents')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

@documents_bp.route('/upload', methods=['POST'])
@token_required
def upload_document():
    if 'document_file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['document_file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    upload_folder = get_upload_folder()
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    new_document = EmployeeDocument(
        employee_id=g.user.employee_profile.id,
        document_type=request.form.get('document_type'),
        document_name=original_filename,
        file_path=file_path,
        file_url=f"/api/documents/download/{unique_filename}"
    )
    db.session.add(new_document)
    db.session.commit()
    return jsonify({'message': 'Document uploaded successfully'}), 201

@documents_bp.route('/download/<filename>')
@token_required
def download_document(filename):
    document = EmployeeDocument.query.filter(EmployeeDocument.file_url.endswith(filename)).first_or_404()
    if document.employee_id != g.user.employee_profile.id and g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
        return jsonify({'message': 'Access denied'}), 403
    return send_file(document.file_path, as_attachment=True)