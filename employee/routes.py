from flask import Blueprint, jsonify, request, g
from models import db
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocuments
from utils.decorators import token_required
import os
from config import Config
from werkzeug.utils import secure_filename

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    if not emp:
        return jsonify({'message': 'Profile not found'}), 404
        
    return jsonify({
        'id': emp.id,
        'first_name': emp.first_name,
        'last_name': emp.last_name,
        'department': emp.department,
        'designation': emp.designation,
        'phone': emp.phone,
        'date_of_joining': emp.date_of_joining
    })

@employee_bp.route('/bank', methods=['GET'])
@token_required
def get_bank():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    bank = EmployeeBankDetails.query.filter_by(employee_id=emp.id).first()
    if not bank:
        return jsonify({})
    return jsonify({
        'bank_name': bank.bank_name,
        'account_number': bank.account_number,
        'ifsc_code': bank.ifsc_code
    })

@employee_bp.route('/bank', methods=['POST'])
@token_required
def add_bank():
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404

    bank = EmployeeBankDetails.query.filter_by(employee_id=emp.id).first()
    if not bank:
        bank = EmployeeBankDetails(employee_id=emp.id)
        db.session.add(bank)
        
    bank.bank_name = data.get('bank_name')
    bank.account_number = data.get('account_number')
    bank.ifsc_code = data.get('ifsc_code')
    
    db.session.commit()
    return jsonify({'message': 'Bank details updated successfully'})

@employee_bp.route('/address', methods=['GET'])
@token_required
def get_address():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    addr = EmployeeAddress.query.filter_by(employee_id=emp.id).first()
    if not addr:
        return jsonify({})
    return jsonify({
        'address_line1': addr.address_line1,
        'city': addr.city,
        'state': addr.state,
        'zip_code': addr.zip_code
    })

@employee_bp.route('/address', methods=['POST'])
@token_required
def add_address():
    data = request.get_json()
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    if not emp:
        return jsonify({'message': 'Employee not found'}), 404

    addr = EmployeeAddress.query.filter_by(employee_id=emp.id).first()
    if not addr:
        addr = EmployeeAddress(employee_id=emp.id)
        db.session.add(addr)
        
    addr.city = data.get('city')
    addr.state = data.get('state')
    addr.zip_code = data.get('zip_code')
    
    db.session.commit()
    return jsonify({'message': 'Address updated successfully'})

@employee_bp.route('/documents', methods=['GET'])
@token_required
def get_documents():
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    docs = EmployeeDocuments.query.filter_by(employee_id=emp.id).all()
    output = []
    for doc in docs:
        output.append({
            'id': doc.id,
            'document_type': doc.document_type,
            'file_name': doc.file_name
        })
    return jsonify({'documents': output})

@employee_bp.route('/document', methods=['POST'])
@token_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    emp = Employee.query.filter_by(user_id=g.user.id).first()
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    doc = EmployeeDocuments(
        employee_id=emp.id,
        document_type=request.form.get('document_type'),
        file_name=filename,
        file_path=file_path
    )
    
    db.session.add(doc)
    db.session.commit()
    return jsonify({'message': 'Document uploaded'})