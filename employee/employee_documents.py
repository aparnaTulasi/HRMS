import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models.master import db
from models.employee_documents import EmployeeDocument

employee_documents_bp = Blueprint('employee_documents', __name__)

# Configuration
UPLOAD_FOLDER = 'uploads/employee_docs'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------
# Upload Document
# -------------------------------
@employee_documents_bp.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Ensure upload directory exists
        abs_upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(abs_upload_path, exist_ok=True)
        
        file_path = os.path.join(abs_upload_path, filename)
        file.save(file_path)
        
        # Get form data
        onboard_id = request.form.get('onboard_id')
        document_type = request.form.get('document_type')
        
        # Validate onboard_id
        if not onboard_id or not onboard_id.strip():
            return jsonify({'error': 'onboard_id is required'}), 400
        try:
            onboard_id = int(onboard_id)
        except ValueError:
            return jsonify({'error': 'Invalid onboard_id'}), 400
        
        new_doc = EmployeeDocument(
            onboard_id=onboard_id,
            document_type=document_type,
            file_name=filename,
            file_path=file_path,
            verified_status='Pending'
        )
        
        db.session.add(new_doc)
        db.session.commit()
        
        return jsonify({'message': 'File uploaded successfully', 'document': new_doc.to_dict()}), 201
    
    return jsonify({'error': 'File type not allowed'}), 400

# -------------------------------
# List Documents by Onboard ID
# -------------------------------
@employee_documents_bp.route('/list/<int:onboard_id>', methods=['GET'])
def get_documents(onboard_id):
    docs = EmployeeDocument.query.filter_by(onboard_id=onboard_id).all()
    return jsonify([doc.to_dict() for doc in docs]), 200

# -------------------------------
# Delete Document
# -------------------------------
@employee_documents_bp.route('/delete/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    doc = EmployeeDocument.query.filter_by(id=doc_id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    # Delete file from system
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted successfully'}), 200

# -------------------------------
# Update Verification Status
# -------------------------------
@employee_documents_bp.route('/verify/<int:doc_id>', methods=['PUT'])
def verify_document(doc_id):
    doc = EmployeeDocument.query.filter_by(id=doc_id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    status = request.json.get('verified_status')
    if status not in ['Pending', 'Verified', 'Rejected']:
        return jsonify({'error': 'Invalid status'}), 400

    doc.verified_status = status
    db.session.commit()
    return jsonify({'message': 'Document status updated', 'document': doc.to_dict()}), 200
