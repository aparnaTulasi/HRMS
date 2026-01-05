from flask import Blueprint, request, jsonify, g, send_from_directory
from werkzeug.utils import secure_filename
import os
import sqlite3
from datetime import datetime
from models.master import Company, UserMaster
from utils.auth_utils import login_required, get_tenant_db_connection
from config import TENANT_FOLDER, EMPLOYEE_DB_FOLDER
from models.master_employee import Employee

employee_documents_bp = Blueprint("employee_documents", __name__)

ALLOWED_DOC_TYPES = [
    "Aadhaar", "PAN", "Resume", "Offer Letter", "Experience Certificate", 
    "Payslips", "Bank Account Proof", "SSC", "Intermediate", 
    "Bachelor Degree", "Other Certificates"
]

def ensure_document_schema(conn):
    """Ensure the documents table exists in Employee DB"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by TEXT,
            uploaded_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            verified_status TEXT DEFAULT 'Pending',
            verified_by TEXT,
            verified_date DATETIME,
            rejection_reason TEXT
        )
    """)
    conn.commit()

@employee_documents_bp.route("/upload", methods=["POST"])
@login_required
def upload_document():
    """Employee uploads a document"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    doc_type = request.form.get('document_type')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if doc_type not in ALLOWED_DOC_TYPES:
        return jsonify({"error": f"Invalid document type. Allowed: {ALLOWED_DOC_TYPES}"}), 400
        
    company = Company.query.get(g.company_id)
    
    # Get Employee DB
    master_emp = Employee.query.filter_by(email=g.email).first()
    if not master_emp:
        return jsonify({"error": "Employee record not found"}), 404
    
    db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{master_emp.id}.db")
    
    try:
        conn = sqlite3.connect(db_path)
        ensure_document_schema(conn)
        cur = conn.cursor()
        
        # Save File
        filename = secure_filename(f"{doc_type}_{int(datetime.now().timestamp())}_{file.filename}")
        upload_dir = os.path.join(EMPLOYEE_DB_FOLDER, "uploads", str(master_emp.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Insert DB Record
        cur.execute("""
            INSERT INTO documents 
            (document_type, file_name, file_path, uploaded_by, verified_status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (doc_type, filename, filename, g.role))
        doc_id = cur.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Document uploaded successfully", "status": "Pending", "document_id": doc_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@employee_documents_bp.route("/my-documents", methods=["GET"])
@login_required
def get_my_documents():
    """List logged-in employee's documents"""
    master_emp = Employee.query.filter_by(email=g.email).first()
    if not master_emp:
        return jsonify({"error": "Employee record not found"}), 404
        
    db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{master_emp.id}.db")
    
    if not os.path.exists(db_path):
         return jsonify([]), 200

    try:
        conn = sqlite3.connect(db_path)
        ensure_document_schema(conn)
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM documents")
        
        columns = [column[0] for column in cur.description]
        docs = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@employee_documents_bp.route("/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id):
    """Delete a document (Only if Pending)"""
    master_emp = Employee.query.filter_by(email=g.email).first()
    if not master_emp:
        return jsonify({"error": "Employee record not found"}), 404
        
    db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{master_emp.id}.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check document status
        cur.execute("SELECT verified_status, file_path FROM documents WHERE document_id = ?", (doc_id,))
        doc = cur.fetchone()
        
        if not doc:
            conn.close()
            return jsonify({"error": "Document not found"}), 404
            
        if doc[0] != 'Pending':
            conn.close()
            return jsonify({"error": "Cannot delete verified or rejected documents"}), 400
            
        # Delete file
        upload_dir = os.path.join(EMPLOYEE_DB_FOLDER, "uploads", str(master_emp.id))
        file_path = os.path.join(upload_dir, doc[1])
        
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
            
        # Delete record
        cur.execute("DELETE FROM documents WHERE document_id = ?", (doc_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Document deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500