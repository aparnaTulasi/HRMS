
from flask import Blueprint, request, jsonify
from models.master import db, Company, UserMaster
from models.rbac import Role
from utils.create_db import create_company_db, seed_admin_user
from utils.auth_utils import login_required, permission_required, hash_password
from werkzeug.security import generate_password_hash

superadmin_bp = Blueprint("superadmin", __name__)

@superadmin_bp.route("/create-company", methods=["POST"])
@login_required
@permission_required("CREATE_COMPANY")
def create_company():
    """Create new company (Super Admin only)"""
    data = request.json
    
    required_fields = ['company_name', 'subdomain', 'admin_email', 'admin_password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400
    
    # Check if subdomain exists
    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({"error": "Subdomain already exists"}), 409
    
    # Check if admin email is globally unique
    if UserMaster.query.filter_by(email=data['admin_email']).first():
        return jsonify({"error": "Email already registered globally"}), 409
    
    # Create company in master DB
    company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain'],
        db_name=data['subdomain'],
        admin_email=data['admin_email'],
        admin_password=generate_password_hash(data['admin_password'])
    )
    
    db.session.add(company)
    db.session.commit()
    
    # Create tenant database
    create_company_db(company.db_name)
    
    # Create admin user in master DB
    admin_user = UserMaster(
        email=data['admin_email'],
        password=hash_password(data['admin_password']),
        role=Role.ADMIN.value,
        company_id=company.id,
        is_active=True
    )
    
    db.session.add(admin_user)
    db.session.commit()
    
    # Seed admin to tenant DB
    seed_admin_user(company.db_name, company.id, data['admin_email'], data['admin_password'])
    
    return jsonify({
        "message": "Company created successfully",
        "company": {
            "id": company.id,
            "name": company.company_name,
            "subdomain": company.subdomain,
            "admin_email": company.admin_email
        },
        "login_url": f"http://{company.subdomain}.hrms.com/login",
        "admin_credentials": {
            "email": data['admin_email'],
            "password": data['admin_password']  # Only returned for initial setup
        }
    }), 201

@superadmin_bp.route("/companies", methods=["GET"])
@login_required
@permission_required("VIEW_ALL_COMPANIES")
def get_all_companies():
    """Get all companies (Super Admin only)"""
    companies = Company.query.all()
    
    result = []
    for company in companies:
        result.append({
            "id": company.id,
            "name": company.company_name,
            "subdomain": company.subdomain,
            "admin_email": company.admin_email,
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "is_active": company.is_active,
            "user_count": UserMaster.query.filter_by(company_id=company.id).count()
        })
    
    return jsonify({"companies": result, "count": len(result)})

@superadmin_bp.route("/company/<int:company_id>", methods=["GET"])
@login_required
@permission_required("VIEW_ALL_COMPANIES")
def get_company(company_id):
    """Get specific company details"""
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({"error": "Company not found"}), 404
    
    users = UserMaster.query.filter_by(company_id=company_id).all()
    
    return jsonify({
        "company": {
            "id": company.id,
            "name": company.company_name,
            "subdomain": company.subdomain,
            "admin_email": company.admin_email,
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "is_active": company.is_active
        },
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None
            } for u in users
        ]
    })

@superadmin_bp.route("/company/<int:company_id>/deactivate", methods=["PUT"])
@login_required
@permission_required("DELETE_COMPANY")
def deactivate_company(company_id):
    """Deactivate a company"""
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({"error": "Company not found"}), 404
    
    company.is_active = False
    db.session.commit()
    
    return jsonify({
        "message": f"Company '{company.company_name}' deactivated",
        "company_id": company.id
    })

@superadmin_bp.route("/company/<int:company_id>/activate", methods=["PUT"])
@login_required
@permission_required("CREATE_COMPANY")
def activate_company(company_id):
    """Activate a company"""
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({"error": "Company not found"}), 404
    
    company.is_active = True
    db.session.commit()
    
    return jsonify({
        "message": f"Company '{company.company_name}' activated",
        "company_id": company.id
    })
