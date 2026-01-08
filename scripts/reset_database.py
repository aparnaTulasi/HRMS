import os
import sqlite3

def reset_database():
    print("🔄 RESETTING DATABASE")
    print("="*50)
    
    # Ensure instance directory exists
    if not os.path.exists('instance'):
        os.makedirs('instance')

    db_path = os.path.join('instance', 'hrms.db')
    
    if os.path.exists(db_path):
        # Backup old database
        backup_path = f'{db_path}.backup'
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(db_path, backup_path)
        print(f"✅ Old database backed up to: {backup_path}")
    
    # Create new database with correct schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create companies table
    cursor.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            company_name VARCHAR(100) NOT NULL,
            subdomain VARCHAR(50) UNIQUE NOT NULL,
            company_code VARCHAR(20) UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(120) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            company_id INTEGER,
            status VARCHAR(20) DEFAULT 'PENDING',
            portal_prefix VARCHAR(50),
            username VARCHAR(50),
            company_code VARCHAR(20),
            otp VARCHAR(6),
            otp_expiry DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)
    
    # Create employees table
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            company_id INTEGER NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            phone VARCHAR(20),
            email VARCHAR(120),
            department VARCHAR(50),
            designation VARCHAR(50),
            date_of_joining VARCHAR(20),
            salary VARCHAR(60),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # Create employee_address table
    cursor.execute("""
        CREATE TABLE employee_address (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER UNIQUE NOT NULL,
            address_line1 VARCHAR(200),
            permanent_address VARCHAR(200),
            city VARCHAR(50),
            state VARCHAR(50),
            zip_code VARCHAR(20),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # Create employee_bank_details table
    cursor.execute("""
        CREATE TABLE employee_bank_details (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER UNIQUE NOT NULL,
            bank_name VARCHAR(100) NOT NULL,
            branch_name VARCHAR(100) NOT NULL,
            account_number VARCHAR(50) NOT NULL,
            ifsc_code VARCHAR(20) NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # Create employee_documents table
    cursor.execute("""
        CREATE TABLE employee_documents (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            document_type VARCHAR(50) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)
    
    print("✅ New database created with correct schema!")
    print("\n📋 Tables created:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for table in cursor.fetchall():
        print(f"  - {table[0]}")
    
    conn.commit()
    conn.close()
    
    print("\n🎉 Database reset complete!")
    print("👉 Restart your Flask app and register users again.")

if __name__ == "__main__":
    reset_database()