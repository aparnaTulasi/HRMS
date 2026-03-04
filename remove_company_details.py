import sqlite3
import os

def remove_company_details():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  Removing Company Details columns (prefix, uid, counter) from 'companies' table...")
    
    try:
        # Check current columns
        cursor.execute("PRAGMA table_info(companies)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 1. Drop Indexes
        print("   - Dropping indexes...")
        cursor.execute("DROP INDEX IF EXISTS ux_companies_company_prefix")
        cursor.execute("DROP INDEX IF EXISTS ux_companies_company_uid")

        # 2. Drop Columns
        # Note: ALTER TABLE DROP COLUMN requires SQLite 3.35.0+
        if 'company_prefix' in columns:
            print("   - Dropping company_prefix...")
            cursor.execute("ALTER TABLE companies DROP COLUMN company_prefix")
            
        if 'company_uid' in columns:
            print("   - Dropping company_uid...")
            cursor.execute("ALTER TABLE companies DROP COLUMN company_uid")
            
        if 'last_user_number' in columns:
            print("   - Dropping last_user_number...")
            cursor.execute("ALTER TABLE companies DROP COLUMN last_user_number")
            
        conn.commit()
        print("✅ Company details columns removed successfully!")
        
    except sqlite3.OperationalError as e:
        print(f"❌ SQLite Error: {e}")
        if "near \"DROP\": syntax error" in str(e):
            print("👉 Your SQLite version might be too old to support DROP COLUMN (Requires 3.35.0+).")
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    remove_company_details()