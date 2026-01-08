from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models import db
from models.company import Company
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json()
    new_company = Company(company_name=data['company_name'], subdomain=data['subdomain'])
    db.session.add(new_company)
    db.session.flush()

    hashed_password = generate_password_hash(data['admin_password'], method='pbkdf2:sha256')
    new_admin = User(email=data['admin_email'], password=hashed_password, role='ADMIN', company_id=new_company.id)
    db.session.add(new_admin)
    db.session.flush()

    admin_emp = Employee(user_id=new_admin.id, company_id=new_company.id, first_name=data.get('admin_first_name', 'Admin'), last_name=data.get('admin_last_name', 'User'))
    db.session.add(admin_emp)
    db.session.commit()
    return jsonify({'message': 'Company and Admin created'}), 201