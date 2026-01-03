from flask import Blueprint, request, jsonify
from models.master import db, Company, UserMaster
from models.rbac import Role
from utils.decorators import jwt_required
from utils.create_db import create_company_db, seed_admin_user
from utils.auth_utils import hash_password

superadmin_bp = Blueprint("superadmin", __name__)

@superadmin_bp.route("/create-company", methods=["POST"])
@jwt_required(roles=[Role.SUPER_ADMIN.value])
def create_company():
    data = request.get_json()
    
    required = ['company_name', 'subdomain', 'admin_email', 'admin_password']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
        
    # Check if subdomain exists
    if Company.query.filter_by(subdomain=data['subdomain']).first():
        return jsonify({"error": "Subdomain already exists"}), 409
        
    # Create Company in Master DB
    new_company = Company(
        company_name=data['company_name'],
        subdomain=data['subdomain'],
        db_name=data['subdomain'],
        admin_email=data['admin_email'],
        admin_password=hash_password(data['admin_password'])
    )
    
    db.session.add(new_company)
    db.session.commit()
    
    # Create Admin User in Master DB automatically
    if not UserMaster.query.filter_by(email=data['admin_email']).first():
        admin_user = UserMaster(
            email=data['admin_email'],
            password=hash_password(data['admin_password']),
            role=Role.ADMIN.value,
            company_id=new_company.id,
            is_active=True,
            status="ACTIVE"
        )
        db.session.add(admin_user)
        db.session.commit()
    
    # Initialize the Tenant Database (SQLite file)
    create_company_db(new_company.db_name)
    
    # Seed Admin in Tenant DB
    seed_admin_user(new_company.db_name, new_company.id, data['admin_email'], hash_password(data['admin_password']))
    
    return jsonify({
        "id": new_company.id,
        "company_name": new_company.company_name,
        "subdomain": new_company.subdomain
    }), 201

@superadmin_bp.route("/companies", methods=["GET"])
@jwt_required(roles=[Role.SUPER_ADMIN.value])
def get_companies():
    companies = Company.query.all()
    result = []
    for c in companies:
        result.append({
            "id": c.id,
            "company_name": c.company_name,
            "subdomain": c.subdomain
        })
    return jsonify(result), 200