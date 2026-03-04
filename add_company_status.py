import sqlite3
import os

def add_company_status():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  Adding 'status' column to 'companies' table...")
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(companies)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'status' not in columns:
            cursor.execute("ALTER TABLE companies ADD COLUMN status TEXT DEFAULT 'Active'")
            print("✅ Added column: status")
        else:
            print("ℹ️  Column 'status' already exists.")
            
        conn.commit()
        print("✅ Database updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_company_status()