import sqlite3
import os

def clear_companies_data():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  Clearing Companies data (and related Users/Employees)...")
    
    try:
        # Helper to safely delete from a table even if it doesn't exist
        def safe_delete(table, where_clause=""):
            try:
                cursor.execute(f"DELETE FROM {table} {where_clause}")
            except sqlite3.OperationalError:
                pass # Table might not exist, skip it

        # 1. Clear Employee related tables first (Child tables of Employees)
        print("   - Clearing Employee details (documents, address, bank)...")
        safe_delete('employee_documents')
        safe_delete('employee_address')
        safe_delete('employee_bank_details')
        
        # 2. Clear Employees
        print("   - Clearing Employees...")
        safe_delete('employees')
        
        # 3. Clear Users linked to companies
        print("   - Clearing Users linked to companies...")
        safe_delete('users', "WHERE company_id IS NOT NULL")

        # 4. Clear Companies
        print("   - Clearing Companies table...")
        safe_delete('companies')
        
        # 5. Reset Auto-Increment Counter for companies
        safe_delete('sqlite_sequence', "WHERE name='companies'")
        
        conn.commit()
        print("✅ Companies data cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clear_companies_data()