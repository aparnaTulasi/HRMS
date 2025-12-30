import os
import sqlite3
from app import app
from models.master import db, Company, UserMaster
from utils.create_db import create_company_db, seed_admin_user, create_tenant_user
from utils.auth_utils import hash_password

# Ensure tenants folder exists
os.makedirs("tenants", exist_ok=True)

def seed_new_schema(db_path, admin_email, admin_password):
    """Seed the new normalized schema tables"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create tables (same as in admin/routes.py)
    cur.execute("""CREATE TABLE IF NOT EXISTS hrms_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS hrms_employee (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, first_name TEXT, last_name TEXT, email TEXT, 
        phone_number TEXT, gender TEXT, date_of_birth DATE, status TEXT DEFAULT 'ACTIVE', FOREIGN KEY(user_id) REFERENCES hrms_users(id))""")
        
    cur.execute("""CREATE TABLE IF NOT EXISTS hrms_job_details (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER UNIQUE, job_title TEXT, department TEXT, 
        designation TEXT, salary REAL, join_date DATE, FOREIGN KEY(employee_id) REFERENCES hrms_employee(id))""")
        
    cur.execute("""CREATE TABLE IF NOT EXISTS hrms_bank_details (
        bank_id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER UNIQUE, bank_name TEXT, account_number TEXT, 
        ifsc_code TEXT, branch_name TEXT, FOREIGN KEY(employee_id) REFERENCES hrms_employee(id))""")
        
    cur.execute("""CREATE TABLE IF NOT EXISTS hrms_address_details (
        address_id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, address_type TEXT, address_line1 TEXT, 
        city TEXT, state TEXT, zip TEXT, country TEXT, FOREIGN KEY(employee_id) REFERENCES hrms_employee(id))""")
    
    # Check if admin exists in new schema
    cur.execute("SELECT id FROM hrms_users WHERE email = ?", (admin_email,))
    if not cur.fetchone():
        # Insert Admin into HRMS_USERS
        cur.execute("INSERT INTO hrms_users (username, email, password, role) VALUES (?, ?, ?, ?)",
                   (admin_email, admin_email, admin_password, 'ADMIN'))
        user_id = cur.lastrowid
        
        # Insert Admin into HRMS_EMPLOYEE
        cur.execute("""
            INSERT INTO hrms_employee (user_id, first_name, last_name, email, status)
            VALUES (?, 'Admin', 'User', ?, 'ACTIVE')
        """, (user_id, admin_email))
        emp_id = cur.lastrowid
        
        # Insert Dummy Job Details
        cur.execute("""
            INSERT INTO hrms_job_details (employee_id, job_title, department, designation)
            VALUES (?, 'System Admin', 'IT', 'Administrator')
        """, (emp_id,))
        
        conn.commit()
        print(f"   ✅ Seeded new schema for {admin_email}")
    
    conn.close()

def seed_employee_new_schema(db_path, name, email, password, role, department="General"):
    """Seed an employee into the new normalized schema"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check if user exists in hrms_users
    cur.execute("SELECT id FROM hrms_users WHERE email = ?", (email,))
    if cur.fetchone():
        conn.close()
        return

    # 1. Insert into HRMS_USERS
    cur.execute("INSERT INTO hrms_users (username, email, password, role) VALUES (?, ?, ?, ?)",
               (email, email, password, role))
    user_id = cur.lastrowid
    
    # 2. Insert into HRMS_EMPLOYEE
    parts = name.split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    
    cur.execute("INSERT INTO hrms_employee (user_id, first_name, last_name, email, status) VALUES (?, ?, ?, ?, 'ACTIVE')",
               (user_id, first_name, last_name, email))
    emp_id = cur.lastrowid
    
    # 3. Insert Dummy Job Details
    cur.execute("INSERT INTO hrms_job_details (employee_id, job_title, department, designation) VALUES (?, ?, ?, ?)",
               (emp_id, role, department, role))
    
    conn.commit()
    conn.close()

with app.app_context():
    print("🚀 Seeding HRMS Database...")
    
    # 1. Create master.db tables
    db.create_all()
    print("✅ Master tables created")
    
    # 2. Create Super Admin if not exists
    super_admin_email = "superadmin@hrms.com"
    super_admin = UserMaster.query.filter_by(email=super_admin_email).first()
    if not super_admin:
        super_admin = UserMaster(
            email=super_admin_email,
            password=hash_password("superadmin123"),
            role="SUPER_ADMIN",
            company_id=None,
            is_active=True
        )
        db.session.add(super_admin)
        db.session.commit()
        print("✅ Super Admin created")
        print(f"   Email: {super_admin_email}")
        print(f"   Password: superadmin123")
    elif not super_admin.is_active:
        super_admin.is_active = True
        super_admin.password = hash_password("superadmin123")
        db.session.commit()
        print("✅ Reactivated Super Admin")
    
    # 3. Create sample companies
    companies_data = [
        {
            "name": "Aparna Corporation",
            "subdomain": "aparna",
            "admin_email": "adminaparna@gmail.com",
            "admin_password": "admin123"
        },
        {
            "name": "Tech Solutions Ltd",
            "subdomain": "tech",
            "admin_email": "admin@tech.com",
            "admin_password": "admin123"
        },
        {
            "name": "Global Enterprises",
            "subdomain": "global",
            "admin_email": "admin@global.com",
            "admin_password": "admin123"
        }
    ]
    
    for company_data in companies_data:
        # Check if company exists
        company = Company.query.filter_by(subdomain=company_data["subdomain"]).first()
        
        if not company:
            # Create company
            company = Company(
                company_name=company_data["name"],
                subdomain=company_data["subdomain"],
                db_name=company_data["subdomain"],
                admin_email=company_data["admin_email"],
                admin_password=hash_password(company_data["admin_password"])
            )
            db.session.add(company)
            db.session.commit()
            
            # Create tenant database
            create_company_db(company.db_name)
            
            # Seed admin to tenant DB
            seed_admin_user(
                company.db_name,
                company.id,
                company_data["admin_email"],
                hash_password(company_data["admin_password"])
            )
            
            # Seed NEW Schema (HRMS_USERS, etc.)
            seed_new_schema(
                os.path.join("tenants", f"{company.db_name}.db"),
                company_data["admin_email"],
                hash_password(company_data["admin_password"])
            )
            
            print(f"✅ Company '{company_data['name']}' created")
            print(f"   Subdomain: {company_data['subdomain']}")
            print(f"   Admin Email: {company_data['admin_email']}")
            print(f"   Admin Password: {company_data['admin_password']}")
            print(f"   Login URL: http://{company_data['subdomain']}.hrms.com/login")
            print()
            
        # Ensure admin user exists in master DB (even if company already existed)
        admin_user = UserMaster.query.filter_by(email=company_data["admin_email"]).first()
        if not admin_user:
            admin_user = UserMaster(
                email=company_data["admin_email"],
                password=hash_password(company_data["admin_password"]),
                role="ADMIN",
                company_id=company.id,
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Restored missing admin user: {company_data['admin_email']}")
        elif not admin_user.is_active:
            admin_user.is_active = True
            admin_user.password = hash_password(company_data["admin_password"])
            db.session.commit()
            print(f"✅ Reactivated admin user: {company_data['admin_email']}")
            
        # Ensure new schema exists even if company existed
        seed_new_schema(
            os.path.join("tenants", f"{company.db_name}.db"),
            company_data["admin_email"],
            hash_password(company_data["admin_password"])
        )
    
    # 4. Create sample employees for Aparna Corp
    aparna_company = Company.query.filter_by(subdomain="aparna").first()
    if aparna_company:
        tenant_db_path = os.path.join("tenants", f"{aparna_company.db_name}.db")
        
        # Check schema safely (close connection before potential delete)
        needs_recreate = False
        if os.path.exists(tenant_db_path):
            conn = sqlite3.connect(tenant_db_path)
            try:
                conn.execute("SELECT company_id FROM users LIMIT 1")
            except sqlite3.OperationalError:
                needs_recreate = True
            finally:
                conn.close()
        
        if needs_recreate:
            print(f"⚠️  Schema mismatch for {aparna_company.subdomain}. Recreating tenant DB...")
            try:
                if os.path.exists(tenant_db_path):
                    os.remove(tenant_db_path)
                create_company_db(aparna_company.db_name)
                seed_admin_user(aparna_company.db_name, aparna_company.id, "adminaparna@gmail.com", hash_password("admin123"))
            except PermissionError:
                print(f"❌ Error: Could not delete {tenant_db_path}. Please close any DB viewers.")

        employees = [
            {"email": "hr@aparna.com", "password": "hr123", "role": "HR_MANAGER", "name": "HR Manager"},
            {"email": "manager@aparna.com", "password": "manager123", "role": "MANAGER", "name": "Team Manager"},
            {"email": "employee@aparna.com", "password": "employee123", "role": "EMPLOYEE", "name": "John Doe"},
            {"email": "accounts@aparna.com", "password": "accounts123", "role": "ACCOUNTS", "name": "Accounts Officer"},
        ]
        
        for emp in employees:
            if not UserMaster.query.filter_by(email=emp["email"]).first():
                user = UserMaster(
                    email=emp["email"],
                    password=hash_password(emp["password"]),
                    role=emp["role"],
                    company_id=aparna_company.id
                )
                db.session.add(user)
            
            # Seed into NEW Schema
            seed_employee_new_schema(
                os.path.join("tenants", f"{aparna_company.db_name}.db"),
                emp["name"],
                emp["email"],
                hash_password(emp["password"]),
                emp["role"]
            )
        
        db.session.commit()
        print("✅ Sample employees added to Aparna Corp")
    
    print("\n🎉 HRMS seeding complete!")
    print("\n📋 Test Credentials:")
    print("1. Super Admin:")
    print("   Email: superadmin@hrms.com")
    print("   Password: superadmin123")
    print("   URL: http://admin.hrms.com/dashboard")
    
    print("\n2. Company Admins:")
    for company_data in companies_data:
        print(f"   Company: {company_data['name']}")
        print(f"   Email: {company_data['admin_email']}")
        print(f"   Password: {company_data['admin_password']}")
        print(f"   URL: http://{company_data['subdomain']}.hrms.com/login")
        print()
