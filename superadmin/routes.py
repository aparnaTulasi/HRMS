from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models import db
from models.company import Company
from sqlalchemy.exc import IntegrityError
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/create-company', methods=['POST'])
@token_required
@role_required(['SUPER_ADMIN'])
def create_company():
    data = request.get_json()
    
    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({'message': 'Subdomain already exists'}), 409

    if User.query.filter_by(email=data['admin_email']).first():
        return jsonify({'message': 'Admin email already exists'}), 409
        
    # 1. Create Company
    new_company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain']
    )
    db.session.add(new_company)    
    
    # 2. Create Admin User
    hashed_password = generate_password_hash(data['admin_password'], method='pbkdf2:sha256')
    new_admin = User(
        email=data['admin_email'],
        password=hashed_password,
        role='ADMIN',
        company=new_company,
        status='ACTIVE',
        portal_prefix='aparna' # As per user request
    )
    db.session.add(new_admin)
    
    # 3. Create Employee Profile for Admin
    admin_emp = Employee(
        user=new_admin,
        company=new_company,
        first_name='Admin',
        last_name='User'
    )
    db.session.add(admin_emp)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'An integrity error occurred. The company or admin might already exist.'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Could not create company.', 'error': str(e)}), 500
    
    return jsonify({'message': 'Company and Admin created successfully'}), 201