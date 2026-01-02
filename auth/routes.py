from flask import Blueprint, request, jsonify, g, current_app
from sqlalchemy import func
import jwt
import random
from models.master import db, UserMaster, Company
from models.rbac import Role
from utils.auth_utils import hash_password, verify_password
from utils.tenant_db import execute_tenant_query
from datetime import datetime
from utils.auth_utils import generate_token
from utils.decorators import jwt_required

auth_bp = Blueprint("auth", __name__)

# Temporary in-memory storage for OTPs (Use Redis in production)
otp_storage = {}

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = UserMaster.query.filter_by(email=data["email"]).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not verify_password(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user.id, user.email, user.role, user.company_id)

    return jsonify({
        "token": token,
        "role": user.role
    })

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user = UserMaster.query.get(g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "company_id": user.company_id
    })

# -------------------------
# REGISTER EMPLOYEE
# -------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Check for token to determine if this is an Admin/HR creating a user
    token = None
    creator_role = None
    creator_company_id = None
    if 'Authorization' in request.headers:
        try:
            token = request.headers['Authorization'].split(" ")[1]
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            creator_role = payload.get('role')
            creator_company_id = payload.get('company_id')
        except:
            pass

    # Required fields (company_subdomain checked later)
    required = ['name', 'email', 'password', 'role']
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Validate role
    try:
        raw_role = str(data['role']).strip().upper()
        if raw_role == "SUPERADMIN":
            raw_role = "SUPER_ADMIN"
        elif raw_role == "HR":
            raw_role = "HR_MANAGER"

        role_enum = Role(raw_role)
    except:
        return jsonify({"error": "Invalid role"}), 400

    # Check email uniqueness
    if UserMaster.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 409

    # ---------------------------------------------------------
    # ROLE & PERMISSION CHECKS
    # ---------------------------------------------------------
    
    # 1. SUPER ADMIN
    if role_enum == Role.SUPER_ADMIN:
        # Allow if it's the first user in the system OR creator is Super Admin
        first_user_exists = UserMaster.query.first() is not None
        
        if first_user_exists and creator_role != Role.SUPER_ADMIN.value:
             return jsonify({"error": "Unauthorized to create Super Admin"}), 403

    # 2. ADMIN
    elif role_enum == Role.ADMIN:
        # Only Super Admin can create Admin
        if creator_role != Role.SUPER_ADMIN.value:
            return jsonify({"error": "Only Super Admin can create Admin users"}), 403

    # 3. HR MANAGER
    elif role_enum == Role.HR_MANAGER:
        # Admin or Super Admin can create HR
        if creator_role not in [Role.SUPER_ADMIN.value, Role.ADMIN.value]:
             return jsonify({"error": "Only Admin or Super Admin can create HR users"}), 403

    # 4. EMPLOYEE (and others)
    else:
        # Admin, HR, or Super Admin can create. Self-signup allowed (no token).
        if creator_role and creator_role not in [Role.SUPER_ADMIN.value, Role.ADMIN.value, Role.HR_MANAGER.value]:
             return jsonify({"error": "Unauthorized to create users"}), 403

    # ---------------------------------------------------------
    # COMPANY VALIDATION
    # ---------------------------------------------------------
    company = None
    
    if role_enum == Role.SUPER_ADMIN:
        # Super Admin is not tied to any company
        company = None
    else:
        # Company required for everyone else
        if 'company_subdomain' in data:
            company = Company.query.filter(func.lower(Company.subdomain) == data['company_subdomain'].strip().lower()).first()
        elif 'company_id' in data:
            company = Company.query.get(data['company_id'])
        else:
             return jsonify({"error": "company_subdomain or company_id is required"}), 400

        if not company:
            return jsonify({"error": "Company not found"}), 404
            
        # Restriction: Admin/HR can only create users for their own company
        if creator_role in [Role.ADMIN.value, Role.HR_MANAGER.value]:
            if creator_company_id != company.id:
                return jsonify({"error": "Unauthorized to create users for a different company"}), 403

    # ---------------------------------------------------------
    # STATUS DETERMINATION
    # ---------------------------------------------------------
    status = "PENDING"
    is_active = False
    
    # If created by an authorized user, set to ACTIVE
    if creator_role:
        status = "ACTIVE"
        is_active = True
        
    # Exception: First Super Admin is always ACTIVE
    if role_enum == Role.SUPER_ADMIN and not creator_role:
        status = "ACTIVE"
        is_active = True

    # Hash password
    hashed_pw = hash_password(data['password'])

    # Create user in master DB
    new_user = UserMaster(
        email=data['email'],
        password=hashed_pw,
        role=role_enum.value,
        company_id=company.id if company else None,
        is_active=is_active,
        status=status
    )
    db.session.add(new_user)
    db.session.commit()

    # Add user in tenant DB (if company exists)
    if company:
        from utils.create_db import create_tenant_user
        create_tenant_user(
            company.db_name,
            company.id,
            data['name'],
            data['email'],
            hashed_pw,
            role_enum.value,
            status=status,
            employee_id=data.get('employee_id'),
            department=data.get('department'),
            designation=data.get('designation'),
            phone=data.get('phone'),
            date_of_joining=data.get('date_of_joining')
        )

    return jsonify({
        "message": f"Registration successful. Status: {status}",
        "user_id": new_user.id
    }), 201

# -------------------------
# PASSWORD & OTP FLOWS
# -------------------------

@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = data.get("email")
    user = UserMaster.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    otp_storage[email] = otp
    
    # In production, send this via Email/SMS
    print(f"🔑 OTP for {email}: {otp}")
    
    return jsonify({"message": "OTP sent successfully (check console)"})

@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")
    
    if otp_storage.get(email) == otp:
        return jsonify({"message": "OTP verified successfully"})
    
    return jsonify({"error": "Invalid OTP"}), 400

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")
    
    if otp_storage.get(email) != otp:
        return jsonify({"error": "Invalid or expired OTP"}), 400
        
    user = UserMaster.query.filter_by(email=email).first()
    user.password = hash_password(new_password)
    db.session.commit()
    
    del otp_storage[email]
    return jsonify({"message": "Password reset successfully"})

@auth_bp.route("/update-password", methods=["POST"])
@jwt_required()
def update_password():
    data = request.get_json()
    user = UserMaster.query.get(g.user_id)
    
    if not verify_password(user.password, data["old_password"]):
        return jsonify({"error": "Incorrect current password"}), 401
        
    user.password = hash_password(data["new_password"])
    db.session.commit()
    
    return jsonify({"message": "Password updated successfully"})
