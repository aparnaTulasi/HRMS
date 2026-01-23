import sqlite3
import os

def add_missing_columns():
    db_path = os.path.join('instance', 'hrms.db')
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking database schema...")
    
    # Check users table columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print("Current columns in users table:")
    for col in columns:
        print(f"  - {col}")
    
    # Add missing columns
    if 'username' not in columns:
        print("\nAdding 'username' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(50)")
        print("✅ Added 'username' column")
    
    if 'company_code' not in columns:
        print("Adding 'company_code' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN company_code VARCHAR(20)")
        print("✅ Added 'company_code' column")
    
    # Check companies table
    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'company_code' not in columns:
        print("\nAdding 'company_code' to companies table...")
        cursor.execute("ALTER TABLE companies ADD COLUMN company_code VARCHAR(20)")
        print("✅ Added 'company_code' to companies table")
    
    if 'timezone' not in columns:
        print("\nAdding 'timezone' to companies table...")
        cursor.execute("ALTER TABLE companies ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC'")
        print("✅ Added 'timezone' to companies table")
    
    conn.commit()
    conn.close()
    print("\n🎉 Database schema updated successfully!")
    print("Restart your Flask app.")

if __name__ == "__main__":
    add_missing_columns()