import sqlite3
import os

def create_company_db(db_name):
    """Creates a new SQLite database for a tenant and initializes tables."""
    # Ensure tenants directory exists
    os.makedirs("tenants", exist_ok=True)
    
    db_path = os.path.join("tenants", f"{db_name}.db")
    
    conn = sqlite3.connect(db_path)
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

    # Departments & Designations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS designations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE CASCADE
        )
    """)

    # Documents & Policies
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES hrms_employee (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attendance
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            date DATE,
            clock_in TIME,
            clock_out TIME,
            status TEXT,
            FOREIGN KEY(employee_id) REFERENCES hrms_employee(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"   Created tenant DB: {db_path}")

def seed_admin_user(db_name, company_id, email, password):
    """Seeds the admin user into the tenant database."""
    db_path = os.path.join("tenants", f"{db_name}.db")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check if user exists in hrms_users
    cur.execute("SELECT id FROM hrms_users WHERE email = ?", (email,))
    if cur.fetchone():
        conn.close()
        return

    # Insert Admin into HRMS_USERS
    cur.execute("INSERT INTO hrms_users (username, email, password, role) VALUES (?, ?, ?, ?)",
               (email, email, password, "ADMIN"))
    user_id = cur.lastrowid
    
    # Insert Admin into HRMS_EMPLOYEE
    cur.execute("""
        INSERT INTO hrms_employee (user_id, first_name, last_name, email, status)
        VALUES (?, 'Admin', 'User', ?, 'ACTIVE')
    """, (user_id, email))
    emp_id = cur.lastrowid
    
    # Insert Dummy Job Details
    cur.execute("""
        INSERT INTO hrms_job_details (employee_id, job_title, department, designation)
        VALUES (?, 'System Admin', 'IT', 'Administrator')
    """, (emp_id,))
    
    conn.commit()
    conn.close()

def create_tenant_user(db_name, company_id, name, email, password, role, status="PENDING", employee_id=None, department=None, designation=None, phone=None, date_of_joining=None):
    """Creates a user in the tenant database using the new schema."""
    db_path = os.path.join("tenants", f"{db_name}.db")
    
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
    
    cur.execute("INSERT INTO hrms_employee (user_id, first_name, last_name, email, status, phone_number) VALUES (?, ?, ?, ?, ?, ?)",
               (user_id, first_name, last_name, email, status, phone))
    emp_id = cur.lastrowid
    
    # 3. Insert Job Details
    cur.execute("INSERT INTO hrms_job_details (employee_id, job_title, department, designation, join_date) VALUES (?, ?, ?, ?, ?)",
               (emp_id, role, department, designation, date_of_joining))
    
    conn.commit()
    conn.close()
