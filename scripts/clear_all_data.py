import sqlite3
import os

def clear_all_data():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  Cleaning up ALL data (Users, Companies, Employees)...")
    
    try:
        # List of tables to clear in order of dependency
        tables_to_clear = [
            'employee_documents',
            'employee_address',
            'employee_bank_details',
            'attendance',
            'leaves',
            'leave_balances',
            'user_permissions',
            'employees',
            'users',
            'companies',
            'departments',
            'system_urls'
        ]
        
        for table in tables_to_clear:
            try:
                print(f"   - Clearing {table}...")
                cursor.execute(f"DELETE FROM {table}")
                # Reset sequence
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            except sqlite3.OperationalError:
                pass # Table might not exist

        conn.commit()
        print("✅ All data removed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clear_all_data()