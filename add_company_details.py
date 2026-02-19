import sqlite3
import os

def add_company_details():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  Adding Company Details columns back to 'companies' table...")
    
    try:
        # 1. Add Columns
        # We use try/except for each column in case they partially exist
        columns_to_add = [
            ("company_prefix", "TEXT"),
            ("company_uid", "TEXT"),
            ("last_user_number", "INTEGER DEFAULT 0")
        ]

        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE companies ADD COLUMN {col_name} {col_type}")
                print(f"   - Added column: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"   - Column {col_name} already exists.")
                else:
                    raise e

        # 2. Add Indexes
        print("   - Creating indexes...")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_companies_company_prefix ON companies(company_prefix)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_companies_company_uid ON companies(company_uid)")
        
        conn.commit()
        print("✅ Company details columns restored successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_company_details()