from flask import Blueprint, request, jsonify, g, current_app
from sqlalchemy import func
import jwt
import random
from models.master import db, UserMaster, Company
from models.rbac import Role
from utils.auth_utils import hash_password, verify_password, generate_token, get_tenant_db_connection
from models.master_employee import Employee
from utils.tenant_db import execute_tenant_query
from datetime import datetime
from utils.decorators import jwt_required
import os
import sqlite3
from config import EMPLOYEE_DB_FOLDER

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

    if not user.is_active:
        return jsonify({"error": "Account is pending approval or deactivated"}), 403

    token = generate_token(user.id, user.email, user.role, user.company_id)

    # -------------------------
    # URL GENERATION LOGIC
    # -------------------------
    username = user.email.split('@')[0]
    subdomain = "portal" # Default fallback if no company
    if user.company_id:
        company = Company.query.get(user.company_id)
        if company:
            subdomain = company.subdomain
            
    redirect_url = f"https://{username}.{subdomain}.com"

    return jsonify({
        "token": token,
        "role": user.role,
        "redirect_url": redirect_url
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
        # EMAIL POLICY ENFORCEMENT
        # ---------------------------------------------------------
        if company.email_domain:
            email = data['email'].lower()
            domain = company.email_domain.lower()
            
            if company.email_policy == "STRICT":
                if not email.endswith(f"@{domain}"):
                    return jsonify({"error": f"Email must end with @{domain} (Strict Policy)"}), 400
            
            elif company.email_policy == "FLEXIBLE":
                allowed_gmail = f".{company.subdomain.lower()}@gmail.com"
                if not (email.endswith(f"@{domain}") or email.endswith(allowed_gmail)):
                    return jsonify({"error": f"Email must end with @{domain} or {allowed_gmail}"}), 400

    # ---------------------------------------------------------
    # STATUS DETERMINATION
    # ---------------------------------------------------------
    status = "PENDING"
    is_active = False
    
    # Rule: Super Admin, Admin, HR are auto-approved (No approval needed)
    if role_enum in [Role.SUPER_ADMIN, Role.ADMIN, Role.HR_MANAGER]:
        status = "ACTIVE"
        is_active = True
    
    # Rule: Employee needs approval, UNLESS created by an authorized user (Admin/HR)
    elif role_enum == Role.EMPLOYEE:
        if creator_role:
            status = "ACTIVE"
            is_active = True
        else:
            status = "PENDING"
            is_active = False

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

    # Add to Master Employee Table (if role is EMPLOYEE)
    if role_enum == Role.EMPLOYEE:
        parts = data['name'].strip().split(' ', 1)
        fname = parts[0]
        lname = parts[1] if len(parts) > 1 else ""
        new_employee_master = Employee(
            name=data['name'],
            first_name=fname,
            last_name=lname,
            email=data['email'],
            password=hashed_pw,
            role=role_enum.value,
            company_subdomain=company.subdomain if company else None,
            department=data.get('department'),
            designation=data.get('designation'),
            phone_number=data.get('phone'),
            date_of_joining=data.get('date_of_joining')
        )
        db.session.add(new_employee_master)
        db.session.commit()

        # Create Employee DB
        emp_db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{new_employee_master.id}.db")
        conn = sqlite3.connect(emp_db_path)
        cur = conn.cursor()
        
        # Initialize Schema (Simplified for brevity, matches admin/routes.py)
        cur.execute("CREATE TABLE IF NOT EXISTS personal_info (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, phone TEXT, gender TEXT, dob DATE, status TEXT DEFAULT 'PENDING')")
        cur.execute("CREATE TABLE IF NOT EXISTS job_details (id INTEGER PRIMARY KEY, job_title TEXT, department TEXT, designation TEXT, salary REAL, join_date DATE)")
        cur.execute("CREATE TABLE IF NOT EXISTS bank_details (id INTEGER PRIMARY KEY, bank_name TEXT, account_number TEXT, ifsc_code TEXT, branch_name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS address_details (id INTEGER PRIMARY KEY, address_line1 TEXT, city TEXT, state TEXT, zip TEXT, country TEXT, address_type TEXT)")
        
        # Insert Data
        cur.execute("INSERT INTO personal_info (first_name, last_name, email, phone, status) VALUES (?, ?, ?, ?, ?)",
                   (fname, lname, data['email'], data.get('phone'), status))
        
        cur.execute("INSERT INTO job_details (department, designation, join_date) VALUES (?, ?, ?)",
                   (data.get('department'), data.get('designation'), data.get('date_of_joining')))
                   
        conn.commit()
        conn.close()

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

# -------------------------
# MASTER EMPLOYEE MANAGEMENT
# -------------------------

@auth_bp.route("/master-employees", methods=["GET"])
@jwt_required(roles=[Role.SUPER_ADMIN.value, Role.ADMIN.value])
def get_master_employees():
    """View all employees in the Master DB Employee table"""
    employees = Employee.query.all()
    result = [{
        "id": e.id,
        "name": e.name,
        "email": e.email,
        "role": e.role,
        "company": e.company_subdomain,
        "department": e.department,
        "designation": e.designation
    } for e in employees]
    return jsonify(result), 200

@auth_bp.route("/sync-employees", methods=["POST"])
@jwt_required(roles=[Role.SUPER_ADMIN.value, Role.ADMIN.value])
def sync_employees():
    """Sync existing tenant users into the Master Employee table"""
    companies = Company.query.all()
    synced_count = 0
    
    for company in companies:
        try:
            conn = get_tenant_db_connection(company.db_name)
            if not conn: continue
            
            cur = conn.cursor()
            # Fetch employee details from Tenant DB
            query = """
                SELECT e.first_name, e.last_name, e.email, e.phone_number, 
                       j.department, j.designation, j.join_date
                FROM hrms_employee e
                LEFT JOIN hrms_job_details j ON e.id = j.employee_id
            """
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            
            for row in rows:
                email = row[2]
                # Check if already exists in Master Employee table
                if not Employee.query.filter_by(email=email).first():
                    # Get password/role from UserMaster
                    master_user = UserMaster.query.filter_by(email=email).first()
                    if master_user:
                        new_emp = Employee(
                            name=f"{row[0]} {row[1]}".strip(),
                            first_name=row[0],
                            last_name=row[1],
                            email=email,
                            password=master_user.password,
                            role=master_user.role,
                            company_subdomain=company.subdomain,
                            phone_number=row[3],
                            department=row[4],
                            designation=row[5],
                            date_of_joining=row[6]
                        )
                        db.session.add(new_emp)
                        synced_count += 1
        except Exception as e:
            print(f"Error syncing company {company.subdomain}: {e}")
            continue
            
    db.session.commit()
    return jsonify({"message": f"Sync complete. {synced_count} employees added to Master DB."}), 200
