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
    
    if 'company_code' in columns:
        print("\nRemoving 'company_code' from users table...")
        try:
            cursor.execute("ALTER TABLE users DROP COLUMN company_code")
            print("✅ Removed 'company_code' from users table")
        except Exception as e:
            print(f"⚠️  Could not remove 'company_code' from users: {e}")
    
    # Check companies table
    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'company_code' not in columns:
        print("\nAdding 'company_code' to companies table...")
        cursor.execute("ALTER TABLE companies ADD COLUMN company_code VARCHAR(20)")
        print("✅ Added 'company_code' to companies table")
    
    if 'timezone' not in columns:
        print("\nAdding 'timezone' to companies table...")
        cursor.execute("ALTER TABLE companies ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Kolkata'")
        print("✅ Added 'timezone' to companies table")
    
    if 'subdomain' not in columns:
        print("\nAdding 'subdomain' to companies table...")
        cursor.execute("ALTER TABLE companies ADD COLUMN subdomain VARCHAR(100)")
        print("✅ Added 'subdomain' to companies table")
    
    conn.commit()
    conn.close()
    print("\n🎉 Database schema updated successfully!")
    print("Restart your Flask app.")

if __name__ == "__main__":
    add_missing_columns()