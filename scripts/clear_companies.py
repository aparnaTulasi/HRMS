import sqlite3
import os

def clear_companies_data():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  Cleaning up Companies data...")
    
    try:
        # 1. Delete Users linked to Companies (So emails can be reused)
        print("   - Deleting users linked to companies...")
        cursor.execute("DELETE FROM users WHERE company_id IS NOT NULL")
        
        # 2. Delete Employees (Employees cannot exist without a company)
        # We need to find employees to delete their related data first
        cursor.execute("SELECT id FROM employees")
        employees = cursor.fetchall()
        
        if employees:
            print(f"   - Deleting {len(employees)} employees and their records...")
            emp_ids = [str(e[0]) for e in employees]
            ids_sql = ",".join(emp_ids)
            
            # Delete related data (ignoring errors if tables don't exist)
            for table in ['employee_documents', 'employee_address', 'employee_bank_details']:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE employee_id IN ({ids_sql})")
                except sqlite3.OperationalError:
                    pass # Table might not exist
            
            cursor.execute(f"DELETE FROM employees WHERE id IN ({ids_sql})")

        # 3. Delete Companies
        print("   - Deleting all companies...")
        cursor.execute("DELETE FROM companies")
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='companies'")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        print("✅ Companies data removed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clear_companies_data()