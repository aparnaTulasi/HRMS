import os

from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.utils import secure_filename
from models.master import db, Company
from models.employee_documents import EmployeeDocument
from utils.auth_utils import login_required, get_tenant_db_connection

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
@login_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    # Determine onboard_id (Employee ID)
    onboard_id = None
    
    # Fetch current employee ID from tenant DB
    company = Company.query.get(g.company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    conn = get_tenant_db_connection(company.db_name)
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM hrms_employee WHERE user_id = ?", (g.user_id,))
        row = cur.fetchone()
        current_emp_id = row[0] if row else None
    finally:
        conn.close()

    if not current_emp_id:
        return jsonify({'error': 'Employee profile not found'}), 404
    onboard_id = current_emp_id

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Ensure upload directory exists
        abs_upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(abs_upload_path, exist_ok=True)
        
        file_path = os.path.join(abs_upload_path, filename)
        file.save(file_path)
        
        document_type = request.form.get('document_type', 'General')
        
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
@login_required
def get_documents(onboard_id):
    # Fetch current employee ID to verify ownership
    company = Company.query.get(g.company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    conn = get_tenant_db_connection(company.db_name)
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM hrms_employee WHERE user_id = ?", (g.user_id,))
        row = cur.fetchone()
        current_emp_id = row[0] if row else None
    finally:
        conn.close()

    if not current_emp_id or current_emp_id != onboard_id:
        return jsonify({'error': 'Unauthorized to view these documents'}), 403

    docs = EmployeeDocument.query.filter_by(onboard_id=onboard_id).all()
    return jsonify([doc.to_dict() for doc in docs]), 200
