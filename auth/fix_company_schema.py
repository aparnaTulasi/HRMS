import sqlite3
import os

def fix_company_schema():
    db_path = "master.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database '{db_path}' not found.")
        return

    print(f"🔍 Checking schema for 'companies' table in {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("PRAGMA table_info(companies)")
        columns = {row[1] for row in cur.fetchall()}
        
        if "email_domain" not in columns:
            print("⚠️  Missing column 'email_domain'. Adding it...")
            cur.execute("ALTER TABLE companies ADD COLUMN email_domain TEXT")
            
        if "email_policy" not in columns:
            print("⚠️  Missing column 'email_policy'. Adding it...")
            cur.execute("ALTER TABLE companies ADD COLUMN email_policy TEXT DEFAULT 'STRICT'")
            
        conn.commit()
        print("✅ Company table schema updated successfully!")
        conn.close()
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")

if __name__ == "__main__":
    fix_company_schema()