import sqlite3
import os
import sys

def delete_company(subdomain):
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"🔍 Attempting to delete company with subdomain: '{subdomain}'...")
    
    try:
        # Find company
        cursor.execute("SELECT id FROM companies WHERE subdomain = ?", (subdomain,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Company '{subdomain}' not found.")
            return
            
        company_id = result[0]
        
        # 1. Unlink Users (Set company_id to NULL for users of this company)
        cursor.execute("UPDATE users SET company_id = NULL WHERE company_id = ?", (company_id,))
        
        # 2. Delete Employees of this company
        cursor.execute("SELECT id FROM employees WHERE company_id = ?", (company_id,))
        employees = cursor.fetchall()
        
        if employees:
            emp_ids = [str(e[0]) for e in employees]
            ids_sql = ",".join(emp_ids)
            
            # Delete related employee data
            for table in ['employee_documents', 'employee_address', 'employee_bank_details']:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE employee_id IN ({ids_sql})")
                except sqlite3.OperationalError:
                    pass
            
            cursor.execute(f"DELETE FROM employees WHERE id IN ({ids_sql})")

        # 3. Delete the Company
        cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        conn.commit()
        print(f"✅ Company '{subdomain}' deleted successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        delete_company(sys.argv[1])
    else:
        # Default to futureinvo if no argument provided
        delete_company("futureinvo")