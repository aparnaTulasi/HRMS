import sqlite3
import os

def add_company_id_column():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking 'companies' table for 'company_id' column...")
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(companies)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'company_id' not in columns:
            print("   - Adding 'company_id' column (VARCHAR)...")
            cursor.execute("ALTER TABLE companies ADD COLUMN company_id VARCHAR(50)")
            print("✅ Added column: company_id")
            
            # Create unique index
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_company_id ON companies(company_id)")
            print("   - Created unique index on company_id")
        else:
            print("ℹ️  Column 'company_id' already exists.")
            
        conn.commit()
        print("✅ Database updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_company_id_column()