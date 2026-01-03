import sqlite3
import os

def fix_employee_schema():
    db_path = "master.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database '{db_path}' not found.")
        return

    print(f"🔍 Checking schema for 'employee' table in {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get columns
        cur.execute("PRAGMA table_info(employee)")
        columns = {row[1] for row in cur.fetchall()}
        
        # Add first_name if missing
        if "first_name" not in columns:
            print("⚠️  Missing column 'first_name'. Adding it...")
            cur.execute("ALTER TABLE employee ADD COLUMN first_name TEXT")
            
        # Add last_name if missing
        if "last_name" not in columns:
            print("⚠️  Missing column 'last_name'. Adding it...")
            cur.execute("ALTER TABLE employee ADD COLUMN last_name TEXT")
            
        conn.commit()
        print("✅ Employee table schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_employee_schema()