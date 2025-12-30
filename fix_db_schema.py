import sqlite3
import os

def fix_master_db_schema():
    db_path = "master.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database '{db_path}' not found. Please ensure you are in the project root.")
        return

    print(f"🔍 Checking schema for database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get columns for users_master table
        cur.execute("PRAGMA table_info(users_master)")
        columns = {row[1] for row in cur.fetchall()}
        
        if "status" not in columns:
            print("⚠️  Missing column 'status' in 'users_master' table.")
            print("🛠️  Applying fix: ALTER TABLE users_master ADD COLUMN status...")
            
            # Add the missing column with a default value
            cur.execute("ALTER TABLE users_master ADD COLUMN status TEXT DEFAULT 'PENDING' NOT NULL")
            
            # Set existing users to ACTIVE so admins don't get locked out
            cur.execute("UPDATE users_master SET status = 'ACTIVE'")
            conn.commit()
            print("✅ Schema updated successfully!")
        else:
            print("✅ Schema is already up to date ('status' column exists).")
            
            # Ensure Admins are ACTIVE (just in case they were set to PENDING previously)
            cur.execute("UPDATE users_master SET status = 'ACTIVE' WHERE role IN ('ADMIN', 'SUPER_ADMIN')")
            conn.commit()
            
    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_master_db_schema()