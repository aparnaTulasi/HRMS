from flask import Blueprint, jsonify, request
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
    """Create company with admin"""
    data = request.get_json()
    
    # Check if company exists
    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({'message': 'Subdomain already exists'}), 409

    # Check if admin email exists
    if User.query.filter_by(email=data['admin_email']).first():
        return jsonify({'message': 'Admin email already exists'}), 409
        
    # 1. Create Company
    new_company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain']
    )
    db.session.add(new_company)
    db.session.flush()
    
    # 2. Create Admin User
    hashed_password = generate_password_hash(data['admin_password'], method='pbkdf2:sha256')
    
    new_admin = User(
        email=data['admin_email'],
        password=hashed_password,
        role='ADMIN',
        company_id=new_company.id,
        status='ACTIVE',
        portal_prefix='aparna'
    )
    db.session.add(new_admin)
    db.session.flush()
    
    # 3. Create Employee Profile for Admin
    admin_emp = Employee(
        user_id=new_admin.id,
        company_id=new_company.id,
        first_name=data.get('admin_first_name', 'Admin'),
        last_name=data.get('admin_last_name', 'User'),
        department='Management',
        designation='Administrator'
    )
    db.session.add(admin_emp)

    try:
        db.session.commit()
        return jsonify({
            'message': 'Company created successfully',
            'company': {
                'id': new_company.id,
                'name': new_company.company_name,
                'subdomain': new_company.subdomain
            },
            'admin': {
                'email': data['admin_email'],
                'password': data['admin_password']  # Return for testing
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating company', 'error': str(e)}), 500

@superadmin_bp.route('/companies', methods=['GET'])
@token_required
@role_required(['SUPER_ADMIN'])
def get_companies():
    """Get all companies"""
    companies = Company.query.all()
    output = []
    
    for company in companies:
        # Get admin user for this company
        admin = User.query.filter_by(company_id=company.id, role='ADMIN').first()
        
        # Count employees in company
        employee_count = Employee.query.filter_by(company_id=company.id).count()
        
        output.append({
            'id': company.id,
            'company_name': company.company_name,
            'subdomain': company.subdomain,
            'created_at': company.created_at.strftime('%Y-%m-%d %H:%M'),
            'admin_email': admin.email if admin else 'No admin',
            'employee_count': employee_count
        })
    
    return jsonify({
        'companies': output,
        'count': len(output)
    })

@superadmin_bp.route('/company/<int:company_id>', methods=['GET'])
@token_required
@role_required(['SUPER_ADMIN'])
def get_company(company_id):
    """Get single company details"""
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'message': 'Company not found'}), 404
    
    # Get admin
    admin = User.query.filter_by(company_id=company.id, role='ADMIN').first()
    
    # Get counts
    admin_count = User.query.filter_by(company_id=company.id, role='ADMIN').count()
    hr_count = User.query.filter_by(company_id=company.id, role='HR').count()
    employee_count = User.query.filter_by(company_id=company.id, role='EMPLOYEE').count()
    
    return jsonify({
        'id': company.id,
        'company_name': company.company_name,
        'subdomain': company.subdomain,
        'created_at': company.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'admin': {
            'email': admin.email if admin else None,
            'name': f"{admin.employee_profile.first_name} {admin.employee_profile.last_name}" if admin and admin.employee_profile else None
        },
        'statistics': {
            'admins': admin_count,
            'hrs': hr_count,
            'employees': employee_count,
            'total': admin_count + hr_count + employee_count
        }
    })