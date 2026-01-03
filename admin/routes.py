
from flask import Blueprint, request, jsonify, g, render_template, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models.master import db, Company, UserMaster
from models.rbac import Role, Permission, RBAC
from models.master_employee import Employee
from utils.auth_utils import login_required, permission_required, get_tenant_db_connection, hash_password
import sqlite3
import os
from config import TENANT_FOLDER, EMPLOYEE_DB_FOLDER

admin_bp = Blueprint("admin", __name__)

def ensure_new_schema(conn):
    """Ensure the new normalized schema exists in the tenant DB"""
    cur = conn.cursor()
    
    # 1. HRMS_USERS (Auth + Role)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hrms_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # 2. HRMS_EMPLOYEE (Profile)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hrms_employee (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone_number TEXT,
            gender TEXT,
            date_of_birth DATE,
            status TEXT DEFAULT 'ACTIVE',
            FOREIGN KEY(user_id) REFERENCES hrms_users(id)
        )
    """)
    
    # 3. HRMS_JOB_DETAILS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hrms_job_details (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER UNIQUE,
            job_title TEXT,
            department TEXT,
            designation TEXT,
            salary REAL,
            join_date DATE,
            FOREIGN KEY(employee_id) REFERENCES hrms_employee(id)
        )
    """)
    
    # 4. HRMS_BANK_DETAILS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hrms_bank_details (
            bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER UNIQUE,
            bank_name TEXT,
            account_number TEXT,
            ifsc_code TEXT,
            branch_name TEXT,
            FOREIGN KEY(employee_id) REFERENCES hrms_employee(id)
        )
    """)
    
    # 5. HRMS_ADDRESS_DETAILS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hrms_address_details (
            address_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            address_type TEXT,
            address_line1 TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            country TEXT,
            FOREIGN KEY(employee_id) REFERENCES hrms_employee(id)
        )
    """)
    
    # 6. EMPLOYEE DOCUMENTS (Robust)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employee_documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by TEXT,
            uploaded_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            verified_status TEXT DEFAULT 'Pending',
            verified_by TEXT,
            verified_date DATETIME,
            FOREIGN KEY(employee_id) REFERENCES hrms_employee(id)
        )
    """)
    conn.commit()

def init_employee_db(db_path):
    """Initialize the schema for a single employee database"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Personal Info
    cur.execute("""
        CREATE TABLE IF NOT EXISTS personal_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT, last_name TEXT, email TEXT, phone TEXT,
            gender TEXT, dob DATE, status TEXT DEFAULT 'ACTIVE'
        )
    """)
    
    # 2. Job Details
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT, department TEXT, designation TEXT,
            salary REAL, join_date DATE
        )
    """)
    
    # 3. Bank Details
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bank_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT, account_number TEXT, ifsc_code TEXT, branch_name TEXT
        )
    """)
    
    # 4. Address Details
    cur.execute("""
        CREATE TABLE IF NOT EXISTS address_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address_line1 TEXT, city TEXT, state TEXT, zip TEXT, country TEXT, address_type TEXT
        )
    """)
    
    # Documents table is handled in employee_documents.py or here if needed
    conn.commit()
    conn.close()

@admin_bp.route("/employees", methods=["GET"])
@login_required
def get_employees():
    """Get all employees in the company"""
    company = Company.query.get(g.company_id)
    if not company:
        return jsonify({"error": "Company not found"}), 404
    
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Tenant database connection failed"}), 500
        
        ensure_new_schema(conn)
        cur = conn.cursor()
        
        # For EMPLOYEE role, only show themselves
        if g.role == 'EMPLOYEE':
            cur.execute("""
                SELECT 
                    e.id, e.first_name, e.last_name, u.email, u.role, 
                    j.department, j.designation, e.phone_number, j.join_date, e.status
                FROM hrms_users u
                JOIN hrms_employee e ON u.id = e.user_id
                LEFT JOIN hrms_job_details j ON e.id = j.employee_id
                WHERE u.email = ?
            """, (g.email,))
        else:
            # ADMIN / HR: Show all
            cur.execute("""
                SELECT 
                    e.id, e.first_name, e.last_name, u.email, u.role, 
                    j.department, j.designation, e.phone_number, j.join_date, e.status
                FROM hrms_users u
                JOIN hrms_employee e ON u.id = e.user_id
                LEFT JOIN hrms_job_details j ON e.id = j.employee_id
                ORDER BY e.first_name
            """)
        
        employees = cur.fetchall()
        
        # Convert to list of dicts
        result = []
        for emp in employees:
            result.append({
                "id": emp[0],
                "name": f"{emp[1]} {emp[2]}",
                "email": emp[3],
                "role": emp[4],
                "department": emp[5],
                "designation": emp[6],
                "phone": emp[7],
                "date_of_joining": emp[8],
                "status": emp[9]
            })
        
        conn.close()
        return jsonify({"employees": result, "count": len(result)})
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/employee", methods=["POST"])
@admin_bp.route("/employees", methods=["POST"])
@login_required
@permission_required(Permission.CREATE_EMPLOYEE)
def create_employee():
    """Create new employee"""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    company = Company.query.get(g.company_id)
    
    # Handle aliases
    if 'phone number' in data and 'phone' not in data:
        data['phone'] = data['phone number']

    # Handle 'name' splitting if first_name/last_name are missing
    if 'name' in data and 'first_name' not in data:
        parts = data['name'].strip().split(' ', 1)
        data['first_name'] = parts[0]
        data['last_name'] = parts[1] if len(parts) > 1 else ""

    # Handle date_of_birth alias
    if 'date_of_birth' in data and 'dob' not in data:
        data['dob'] = data['date_of_birth']

    required_fields = ['first_name', 'last_name', 'email', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400
    
    # Validate Role
    try:
        role_enum = Role(data['role'].strip().upper())
    except (ValueError, AttributeError):
        return jsonify({"error": f"Invalid role. Allowed: {[r.value for r in Role]}"}), 400

    # Check if email is globally unique
    existing_user = UserMaster.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({"error": "Email already registered globally"}), 409
    
    try:
        # Add to master DB
        new_user = UserMaster(
            email=data['email'],
            password=hash_password(data['password']),
            role=role_enum.value,
            company_id=g.company_id,
            is_active=True
        )
        db.session.add(new_user)
        
        # Sync to Master Employee Table (Global Directory)
        new_master_emp = None
        if role_enum == Role.EMPLOYEE:
            job_info = data.get('job', {})
            new_master_emp = Employee(
                name=f"{data['first_name']} {data['last_name']}",
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                password=new_user.password,
                role=role_enum.value,
                company_subdomain=company.subdomain,
                phone_number=data.get('phone') or data.get('phone number'),
                department=job_info.get('department') or data.get('department'),
                designation=job_info.get('designation') or data.get('designation'),
                date_of_joining=job_info.get('join_date') or data.get('date_of_joining')
            )
            db.session.add(new_master_emp)
            
        db.session.commit()
        
        # Create Individual Employee Database
        if new_master_emp:
            emp_db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{new_master_emp.id}.db")
            init_employee_db(emp_db_path)
            
            # Insert Data into Employee DB
            emp_conn = sqlite3.connect(emp_db_path)
            emp_cur = emp_conn.cursor()
            
            job_data = data.get('job', {})
            bank_data = data.get('bank', {})
            address_data = data.get('address', {})
            
            emp_cur.execute("INSERT INTO personal_info (first_name, last_name, email, phone, gender, dob) VALUES (?, ?, ?, ?, ?, ?)",
                           (data['first_name'], data['last_name'], data['email'], data.get('phone'), data.get('gender'), data.get('dob')))
            
            emp_cur.execute("INSERT INTO job_details (job_title, department, designation, salary, join_date) VALUES (?, ?, ?, ?, ?)",
                           (job_data.get('job_title'), job_data.get('department'), job_data.get('designation'), job_data.get('salary'), job_data.get('join_date')))
            
            emp_cur.execute("INSERT INTO bank_details (bank_name, account_number, ifsc_code, branch_name) VALUES (?, ?, ?, ?)",
                           (bank_data.get('bank_name'), bank_data.get('account_number'), bank_data.get('ifsc_code'), bank_data.get('branch_name')))
            
            emp_cur.execute("INSERT INTO address_details (address_line1, city, state, zip, country, address_type) VALUES (?, ?, ?, ?, ?, ?)",
                           (address_data.get('address_line1'), address_data.get('city'), address_data.get('state'), address_data.get('zip'), address_data.get('country'), address_data.get('address_type')))
            
            emp_conn.commit()
            emp_conn.close()

        try:
            # Keep Tenant DB logic for Auth/User mapping if needed, or rely on Master
            pass 
        except Exception as e:
            conn.rollback()
            # Cleanup Master DB
            db.session.delete(new_user)
            db.session.commit()
            conn.close()
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

        
        return jsonify({
            "message": "Employee created successfully",
            "employee_id": new_master_emp.id if new_master_emp else None,
            "user": {
                "id": user_id,
                "email": new_user.email,
                "role": new_user.role,
                "company_id": new_user.company_id
            }
        }), 201
        
    except sqlite3.Error as e:
        # Rollback Master DB creation since Tenant DB failed
        db.session.delete(new_user)
        db.session.commit()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/employee/<int:employee_id>", methods=["GET"])
@admin_bp.route("/employees/<int:employee_id>", methods=["GET"])
@login_required
def get_employee(employee_id):
    """Get specific employee details"""
    # Connect to Employee's specific DB
    db_path = os.path.join(EMPLOYEE_DB_FOLDER, f"emp_{employee_id}.db")
    if not os.path.exists(db_path):
        return jsonify({"error": "Employee database not found"}), 404
        
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM personal_info LIMIT 1")
        personal = cur.fetchone()
        cur.execute("SELECT * FROM job_details LIMIT 1")
        job = cur.fetchone()
        cur.execute("SELECT * FROM bank_details LIMIT 1")
        bank = cur.fetchone()
        cur.execute("SELECT * FROM address_details LIMIT 1")
        addr = cur.fetchone()
        
        conn.close()
        
        # Check RBAC permissions
        if not RBAC.can_access_employee(
            Role(g.role), 
            g.company_id, 
            g.company_id,  # Same company
            g.user_id if g.role == Role.EMPLOYEE.value else None,
            employee_id
        ):
            return jsonify({"error": "Access denied"}), 403
        
        return jsonify({
            "id": employee_id,
            "name": f"{personal[1]} {personal[2]}" if personal else "",
            "email": personal[3] if personal else "",
            "phone": personal[4] if personal else "",
            "status": personal[7] if personal else "ACTIVE",
            "department": job[2] if job else "",
            "designation": job[3] if job else "",
            "date_of_joining": job[5] if job else "",
            "details": {
                "salary": job[4] if job else 0,
                "bank": bank[1] if bank else "",
                "account": bank[2] if bank else "",
                "city": addr[2] if addr else ""
            }
        })
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/employee/<int:employee_id>", methods=["PUT"])
@admin_bp.route("/employees/<int:employee_id>", methods=["PUT"])
@login_required
def update_employee(employee_id):
    """Update employee details"""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    company = Company.query.get(g.company_id)
    
    # Handle aliases
    if 'phone number' in data and 'phone' not in data:
        data['phone'] = data['phone number']
    
    # Check if employee exists and belongs to same company
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Tenant database connection failed"}), 500
        cur = conn.cursor()
        
        # Fetch current details (including job details) for sync
        cur.execute("""
            SELECT e.id, u.email, e.first_name, e.last_name, e.phone_number, 
                   j.department, j.designation 
            FROM hrms_employee e 
            JOIN hrms_users u ON e.user_id = u.id 
            LEFT JOIN hrms_job_details j ON e.id = j.employee_id
            WHERE e.id = ?
        """, (employee_id,))
        
        user_row = cur.fetchone()
        if not user_row:
            conn.close()
            return jsonify({"error": "Employee not found"}), 404
        
        # Authorization Check:
        # 1. Employees can only update themselves.
        # 2. HR/Admin can update anyone.
        if g.role == 'EMPLOYEE' and user_row[1] != g.email:
            conn.close()
            return jsonify({"error": "Unauthorized: You can only update your own profile"}), 403
            
        # Prevent self-deactivation
        if 'status' in data and data['status'] != 'ACTIVE' and user_row[1] == g.email:
            conn.close()
            return jsonify({"error": "You cannot deactivate your own account"}), 403

        # Build update query
        # Updating HRMS_EMPLOYEE
        if 'first_name' in data:
            cur.execute("UPDATE hrms_employee SET first_name = ? WHERE id = ?", (data['first_name'], employee_id))
        if 'last_name' in data:
            cur.execute("UPDATE hrms_employee SET last_name = ? WHERE id = ?", (data['last_name'], employee_id))
        if 'phone' in data:
            cur.execute("UPDATE hrms_employee SET phone_number = ? WHERE id = ?", (data['phone'], employee_id))
        if 'status' in data:
            cur.execute("UPDATE hrms_employee SET status = ? WHERE id = ?", (data['status'], employee_id))
            
        # Updating HRMS_JOB_DETAILS
        if 'department' in data:
            cur.execute("UPDATE hrms_job_details SET department = ? WHERE employee_id = ?", (data['department'], employee_id))
        if 'designation' in data:
            cur.execute("UPDATE hrms_job_details SET designation = ? WHERE employee_id = ?", (data['designation'], employee_id))
        if 'salary' in data:
            cur.execute("UPDATE hrms_job_details SET salary = ? WHERE employee_id = ?", (data['salary'], employee_id))
        if 'job_title' in data:
            cur.execute("UPDATE hrms_job_details SET job_title = ? WHERE employee_id = ?", (data['job_title'], employee_id))
        if 'join_date' in data:
            cur.execute("UPDATE hrms_job_details SET join_date = ? WHERE employee_id = ?", (data['join_date'], employee_id))
            
        # Capture updated values for sync (or fallback to existing)
        new_first_name = data.get('first_name', user_row[2] or "")
        new_last_name = data.get('last_name', user_row[3] or "")
        new_phone = data.get('phone', user_row[4])
        new_dept = data.get('department', user_row[5])
        new_desig = data.get('designation', user_row[6])

        conn.commit()
        conn.close()
        
        # Sync changes to Master DB
        from models.master import UserMaster
        from models.master_employee import Employee
        
        # 1. Update UserMaster (Auth)
        if 'role' in data or 'status' in data:
            master_user = UserMaster.query.filter_by(email=user_row[1]).first()
            if master_user:
                if 'role' in data:
                    master_user.role = data['role']
                if 'status' in data:
                    master_user.is_active = (data['status'] == 'ACTIVE')
        
        # 2. Update Master Employee Table (Global Directory)
        master_emp = Employee.query.filter_by(email=user_row[1]).first()
        
        if not master_emp:
            # Create if missing (Upsert)
            master_user_auth = UserMaster.query.filter_by(email=user_row[1]).first()
            if master_user_auth:
                master_emp = Employee(
                    name=f"{new_first_name} {new_last_name}".strip(),
                    first_name=new_first_name,
                    last_name=new_last_name,
                    email=user_row[1],
                    password=master_user_auth.password,
                    role=master_user_auth.role,
                    company_subdomain=company.subdomain,
                    phone_number=new_phone,
                    department=new_dept,
                    designation=new_desig
                )
                db.session.add(master_emp)
        else:
            master_emp.name = f"{new_first_name} {new_last_name}".strip()
            master_emp.first_name = new_first_name
            master_emp.last_name = new_last_name
            master_emp.phone_number = new_phone
            master_emp.department = new_dept
            master_emp.designation = new_desig
        
        db.session.commit()
        
        return jsonify({"message": "Employee updated successfully"})
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/employee/<int:employee_id>", methods=["DELETE"])
@admin_bp.route("/employees/<int:employee_id>", methods=["DELETE"])
@login_required
@permission_required(Permission.DELETE_EMPLOYEE)
def delete_employee(employee_id):
    """Delete employee (soft delete)"""
    company = Company.query.get(g.company_id)
    
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Tenant database connection failed"}), 500
        cur = conn.cursor()
        
        # Get employee email first for Master DB sync
        cur.execute("SELECT u.email FROM hrms_employee e JOIN hrms_users u ON e.user_id = u.id WHERE e.id = ?", (employee_id,))
        emp_row = cur.fetchone()
        
        if not emp_row:
            conn.close()
            return jsonify({"error": "Employee not found"}), 404
            
        target_email = emp_row[0]
        
        if target_email == g.email:
            conn.close()
            return jsonify({"error": "You cannot delete your own account"}), 403

        # Soft delete in HRMS_EMPLOYEE
        cur.execute("""
            UPDATE hrms_employee SET status = 'INACTIVE' WHERE id = ?
        """, (employee_id,))
        
        conn.commit()
        conn.close()
        
        # Also deactivate in master DB
        from models.master import UserMaster
        user = UserMaster.query.filter_by(email=target_email, company_id=g.company_id).first()
        if user:
            user.is_active = False
            db.session.commit()
        
        return jsonify({"message": "Employee deactivated successfully"})
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/pending-approvals", methods=["GET"])
@login_required
@permission_required(Permission.CREATE_EMPLOYEE)
def get_pending_approvals():
    """Get users pending approval"""
    company = Company.query.get(g.company_id)
    
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Tenant database connection failed"}), 500
        cur = conn.cursor()
        
        cur.execute("""
            SELECT u.id, e.first_name || ' ' || e.last_name, u.email, u.role, j.department
            FROM hrms_users u
            JOIN hrms_employee e ON u.id = e.user_id
            LEFT JOIN hrms_job_details j ON e.id = j.employee_id
            WHERE e.status = 'PENDING'
        """)
        
        pending_users = cur.fetchall()
        conn.close()
        
        result = []
        for user in pending_users:
            result.append({
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "role": user[3],
                "department": user[4]
            })
        
        return jsonify({"pending_users": result, "count": len(result)})
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/approve-user/<int:user_id>", methods=["POST"])
@login_required
@permission_required(Permission.APPROVE_USER)
def approve_user(user_id):
    """Approve a pending user registration"""
    # 1. Look up in Master DB first (Source of Truth for ID)
    master_user = UserMaster.query.get(user_id)
    if not master_user:
        return jsonify({"error": "User not found"}), 404
        
    if master_user.company_id != g.company_id:
        return jsonify({"error": "Unauthorized"}), 403

    if master_user.status == 'ACTIVE':
        return jsonify({"message": "User is already active"}), 200

    # 2. Update Master DB
    master_user.status = 'ACTIVE'
    master_user.is_active = True
    db.session.commit()

    # 3. Update Tenant DB
    company = Company.query.get(g.company_id)
    
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "Tenant database connection failed"}), 500
        cur = conn.cursor()
        
        # Find tenant user ID by email
        cur.execute("SELECT id FROM hrms_users WHERE email = ?", (master_user.email,))
        row = cur.fetchone()
        
        if row:
            tenant_user_id = row[0]
            # Update status in hrms_employee
            cur.execute("UPDATE hrms_employee SET status = 'ACTIVE' WHERE user_id = ?", (tenant_user_id,))
            conn.commit()
        
        conn.close()
            
        # Mock Email Notification
        print(f"\n📧 [MOCK EMAIL] To: {master_user.email}")
        print(f"Subject: Account Approved")
        print(f"Message: Your account has been approved.\n")
            
        return jsonify({"message": "User approved successfully"})
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@admin_bp.route("/companies", methods=["GET"])
@login_required
def get_companies():
    """Get all registered companies (Super Admin only)"""
    if g.role != Role.SUPER_ADMIN.value:
        return jsonify({"error": "Access denied. Super Admin only."}), 403
        
    companies = Company.query.all()
    
    result = []
    for comp in companies:
        result.append({
            "id": comp.id,
            "name": comp.company_name,
            "subdomain": comp.subdomain,
            "admin_email": comp.admin_email,
            "db_name": comp.db_name
        })
        
    return jsonify({"companies": result, "count": len(result)})

@admin_bp.route("/dashboard-view", methods=["GET"])
def dashboard_view():
    """Serve the frontend dashboard (Employee Master UI)"""
    return render_template("dashboard.html")

@admin_bp.route("/dashboard-stats", methods=["GET"])
@login_required
def get_dashboard_stats():
    """Get dashboard statistics (Admin/HR)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        
        # 1. Total Active Employees
        cur.execute("SELECT COUNT(*) FROM hrms_employee WHERE status = 'ACTIVE'")
        total_employees = cur.fetchone()[0]
        
        # 2. Pending Documents
        cur.execute("SELECT COUNT(*) FROM employee_documents WHERE verified_status = 'Pending'")
        pending_docs = cur.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total_employees": total_employees,
            "pending_documents": pending_docs
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/hard-delete-user/<int:user_id>", methods=["DELETE"])
def hard_delete_user(user_id):
    """
    DEV ENDPOINT: Permanently delete a user (Hard Delete).
    Useful for clearing test data to reuse emails.
    """
    from models.master import UserMaster
    
    # 1. Get User from Master DB
    user = UserMaster.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    company_id = user.company_id
    email = user.email
    
    try:
        # 2. Delete from Tenant DB (if exists)
        if company_id:
            company = Company.query.get(company_id)
            if company:
                conn = get_tenant_db_connection(company.db_name)
                if conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM hrms_users WHERE email = ?", (email,))
                    conn.commit()
                    conn.close()
        
        # 3. Delete from Master DB
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({"message": f"User {email} permanently deleted."}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ==========================================
# Departments & Designations APIs
# ==========================================

@admin_bp.route("/departments", methods=["GET"])
@login_required
def get_departments():
    """List all departments"""
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        if not conn:
            return jsonify({"error": "DB connection failed"}), 500
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM departments ORDER BY name")
        depts = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
        conn.close()
        return jsonify(depts)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/document/<int:doc_id>/download", methods=["GET"])
@login_required
def download_document(doc_id):
    """Download a specific document"""
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        
        # Updated to use employee_documents and join with hrms_employee to check user_id
        cur.execute("""
            SELECT d.file_path, e.user_id 
            FROM employee_documents d
            JOIN hrms_employee e ON d.employee_id = e.id
            WHERE d.document_id = ?
        """, (doc_id,))
        doc = cur.fetchone()
        conn.close()
        
        if not doc:
            return jsonify({"error": "Document not found"}), 404
            
        # Access Check: Employees can only download their own docs; Admin/HR can download any
        if g.role == 'EMPLOYEE' and doc[1] != g.user_id:
            return jsonify({"error": "Unauthorized"}), 403
            
        upload_dir = os.path.join(TENANT_FOLDER, "uploads", company.db_name)
        return send_from_directory(upload_dir, doc[0], as_attachment=True)
        
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/department", methods=["POST"])
@login_required
def create_department():
    """Create a new department (Admin/HR only)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json(force=True, silent=True)
    if not data or 'name' not in data:
        return jsonify({"error": "Department name is required"}), 400
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO departments (name) VALUES (?)", (data['name'],))
        conn.commit()
        dept_id = cur.lastrowid
        conn.close()
        return jsonify({"message": "Department created", "id": dept_id}), 201
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/department/<int:dept_id>", methods=["DELETE"])
@login_required
def delete_department(dept_id):
    """Delete a department (Admin/HR only)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        cur.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Department deleted"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/designations", methods=["GET"])
@login_required
def get_designations():
    """List designations (optionally filtered by department_id)"""
    dept_id = request.args.get('department_id')
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        
        query = "SELECT d.id, d.name, d.department_id, dep.name as dept_name FROM designations d LEFT JOIN departments dep ON d.department_id = dep.id"
        params = []
        if dept_id:
            query += " WHERE d.department_id = ?"
            params.append(dept_id)
        query += " ORDER BY d.name"
        
        cur.execute(query, params)
        desigs = [{
            "id": r[0], 
            "name": r[1], 
            "department_id": r[2],
            "department_name": r[3]
        } for r in cur.fetchall()]
        conn.close()
        return jsonify(desigs)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/designation", methods=["POST"])
@login_required
def create_designation():
    """Create a new designation (Admin/HR only)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json(force=True, silent=True)
    if not data or 'name' not in data or 'department_id' not in data:
        return jsonify({"error": "Name and department_id are required"}), 400
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO designations (department_id, name) VALUES (?, ?)", (data['department_id'], data['name']))
        conn.commit()
        desig_id = cur.lastrowid
        conn.close()
        return jsonify({"message": "Designation created", "id": desig_id}), 201
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# Employee Document APIs
# ==========================================

@admin_bp.route("/employee/<int:emp_id>/documents", methods=["POST"])
@login_required
def upload_document(emp_id):
    """Upload a document for an employee (Admin/HR only)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    if 'file' not in request.files or 'document_type' not in request.form:
        return jsonify({"error": "File and document_type are required"}), 400
        
    file = request.files['file']
    doc_type = request.form['document_type']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    company = Company.query.get(g.company_id)
    # Unique filename
    filename = secure_filename(f"{doc_type}_{file.filename}")
    
    # Ensure upload directory exists
    upload_dir = os.path.join(TENANT_FOLDER, "uploads", company.db_name, str(emp_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    try:
        conn = get_tenant_db_connection(company.db_name)
        ensure_new_schema(conn)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO employee_documents 
            (employee_id, document_type, file_name, file_path, uploaded_by, verified_status)
            VALUES (?, ?, ?, ?, ?, 'Verified')
        """, (emp_id, doc_type, filename, f"{emp_id}/{filename}", g.role))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Document uploaded successfully"}), 201
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/employee/<int:emp_id>/documents", methods=["GET"])
@login_required
def get_documents(emp_id):
    """Get documents for an employee"""
    # Access Control: Admin/HR or the employee themselves
    conn = None
    try:
        company = Company.query.get(g.company_id)
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        
        # Check if table exists (backward compatibility)
        try:
            cur.execute("SELECT * FROM employee_documents WHERE employee_id = ?", (emp_id,))
            columns = [column[0] for column in cur.description]
            docs = [dict(zip(columns, row)) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            return jsonify([])
            
        return jsonify(docs)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@admin_bp.route("/document/<int:doc_id>/verify", methods=["PUT"])
@login_required
def verify_document(doc_id):
    """Verify or Reject a document (Admin/HR only)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    if isinstance(data, list):
        data = data[0] if data else {}

    status = data.get('status') or data.get('verified_status')
    
    if status not in ['Verified', 'Rejected']:
        return jsonify({"error": "Invalid status. Use 'Verified' or 'Rejected'"}), 400
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        
        from datetime import datetime
        now = datetime.now()
        
        cur.execute("""
            UPDATE employee_documents 
            SET verified_status = ?, verified_by = ?, verified_date = ?
            WHERE document_id = ?
        """, (status, g.email, now, doc_id))
        
        # Mock Email Notification for Rejection
        if status == 'Rejected':
            cur.execute("""
                SELECT e.email, d.document_type 
                FROM employee_documents d
                JOIN hrms_employee e ON d.employee_id = e.id
                WHERE d.document_id = ?
            """, (doc_id,))
            row = cur.fetchone()
            if row:
                print(f"\n📧 [MOCK EMAIL] To: {row[0]}")
                print(f"Subject: Document Rejected - {row[1]}")
                print(f"Message: Your uploaded document has been rejected. Please upload a valid copy.\n")
        
        conn.commit()
        conn.close()
        return jsonify({"message": f"Document marked as {status}"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/document/<int:doc_id>/update", methods=["PUT"])
@login_required
def update_document_details(doc_id):
    """Update document type (Admin/HR only) - Cannot change file"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    new_type = data.get('document_type')
    
    if not new_type:
        return jsonify({"error": "document_type is required"}), 400
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        cur.execute("UPDATE employee_documents SET document_type = ? WHERE document_id = ?", (new_type, doc_id))
        conn.commit()
        conn.close()
        return jsonify({"message": "Document details updated"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# Policy Management APIs
# ==========================================

@admin_bp.route("/policies", methods=["GET"])
@login_required
def get_policies():
    """List all company policies"""
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, created_at FROM policies ORDER BY created_at DESC")
        policies = [{"id": r[0], "title": r[1], "content": r[2], "created_at": r[3]} for r in cur.fetchall()]
        conn.close()
        return jsonify(policies)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/policy", methods=["POST"])
@login_required
def create_policy():
    """Create a new policy (Admin/HR only)"""
    if g.role not in [Role.ADMIN.value, Role.HR_MANAGER.value, Role.SUPER_ADMIN.value]:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json(force=True, silent=True)
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
        
    company = Company.query.get(g.company_id)
    try:
        conn = get_tenant_db_connection(company.db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO policies (title, content) VALUES (?, ?)", 
                   (data['title'], data.get('content', '')))
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return jsonify({"message": "Policy created", "id": pid}), 201
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/hard-delete-company/<string:subdomain>", methods=["DELETE"])
def hard_delete_company(subdomain):
    """
    DEV ENDPOINT: Permanently delete a company and its associated master users.
    Useful for resetting a company registration.
    """
    # 1. Get Company
    company = Company.query.filter_by(subdomain=subdomain).first()
    if not company:
        return jsonify({"error": "Company not found"}), 404
        
    try:
        # 2. Delete all Master Users associated with this company
        UserMaster.query.filter_by(company_id=company.id).delete()
        
        # 3. Delete Company record
        db.session.delete(company)
        db.session.commit()
        
        # 4. Delete Tenant DB file
        db_path = os.path.join("tenants", f"{company.db_name}.db")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"⚠️ Could not delete DB file: {e}")

        return jsonify({"message": f"Company {subdomain} and associated users deleted."}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500