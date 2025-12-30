from flask import Blueprint, request, jsonify, g
from sqlalchemy import func
from models.master import db, UserMaster, Company
from models.rbac import Role
from utils.auth_utils import hash_password, login_required
from utils.tenant_db import execute_tenant_query
from datetime import datetime

auth_bp = Blueprint("auth", __name__)

# -------------------------
# REGISTER EMPLOYEE
# -------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Required fields
    required = ['name', 'email', 'password', 'company_subdomain', 'role']
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Check email uniqueness
    if UserMaster.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 409

    # Get company
    company = Company.query.filter(func.lower(Company.subdomain) == data['company_subdomain'].lower()).first()
    if not company:
        return jsonify({"error": "Company not found"}), 404

    # Validate role
    try:
        role = Role(data['role'].upper())
    except:
        return jsonify({"error": "Invalid role"}), 400

    # Hash password
    hashed_pw = hash_password(data['password'])

    # Create user in master DB with status PENDING
    new_user = UserMaster(
        email=data['email'],
        password=hashed_pw,
        role=role.value,
        company_id=company.id,
        is_active=False,
        status="PENDING"
    )
    db.session.add(new_user)
    db.session.commit()

    # Add user in tenant DB
    from utils.create_db import create_tenant_user
    create_tenant_user(
        company.db_name,
        company.id,
        data['name'],
        data['email'],
        hashed_pw,
        role.value,
        status="PENDING",
        employee_id=data.get('employee_id'),
        department=data.get('department'),
        designation=data.get('designation'),
        phone=data.get('phone'),
        date_of_joining=data.get('date_of_joining')
    )

    return jsonify({
        "message": "Registration successful. Awaiting admin approval.",
        "user_id": new_user.id
    }), 201

# -------------------------
# ADMIN: GET PENDING USERS
# -------------------------
@auth_bp.route("/admin/pending-approvals", methods=["GET"])
@login_required
def pending_approvals():
    # Only admin or super admin
    if g.user_role not in [Role.ADMIN.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403

    pending_users = UserMaster.query.filter_by(status="PENDING").all()
    result = []
    for user in pending_users:
        company = Company.query.get(user.company_id) if user.company_id else None
        result.append({
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "company_id": company.id if company else None,
            "company_name": company.company_name if company else None,
            "subdomain": company.subdomain if company else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
    return jsonify({"count": len(result), "pending_users": result}), 200

# -------------------------
# ADMIN: APPROVE USER
# -------------------------
@auth_bp.route("/admin/approve-user/<int:user_id>", methods=["POST"])
@login_required
def approve_user(user_id):
    if g.user_role not in [Role.ADMIN.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403

    user = UserMaster.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.status != "PENDING":
        return jsonify({"error": f"User status is {user.status}, cannot approve"}), 400

    # Update master DB
    user.status = "ACTIVE"
    user.is_active = True
    db.session.commit()

    # Update tenant DB
    if user.company_id:
        execute_tenant_query(
            user.company_id,
            "UPDATE hrms_employee SET status = ? WHERE email = ?",
            ("ACTIVE", user.email),
            commit=True
        )

    return jsonify({"message": f"User {user.email} approved successfully"}), 200
