import sqlite3
import os

def delete_managers():
    """
    Deletes all users with role 'MANAGER' and their associated employee data.
    """
    # Path to the database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        print("🔍 Searching for users with role 'MANAGER'...")
        cursor.execute("SELECT id, email FROM users WHERE role = 'MANAGER'")
        managers = cursor.fetchall()

        if not managers:
            print("✅ No managers found to delete.")
            return

        print(f"⚠️  Found {len(managers)} manager(s):")
        for m in managers:
            print(f"   - ID: {m[0]}, Email: {m[1]}")

        confirm = input("\nAre you sure you want to delete these managers? (yes/no): ")
        if confirm.lower() != 'yes':
            print("🚫 Operation cancelled.")
            return

        manager_user_ids = [m[0] for m in managers]
        placeholders = ','.join('?' for _ in manager_user_ids)

        # 1. Find associated employees
        cursor.execute(f"SELECT id FROM employees WHERE user_id IN ({placeholders})", manager_user_ids)
        emp_ids = [row[0] for row in cursor.fetchall()]

        if emp_ids:
            emp_placeholders = ','.join('?' for _ in emp_ids)
            
            # 2. Clean up dependencies
            print("   Cleaning up employee dependencies...")
            
            # Payslips
            cursor.execute(f"SELECT id FROM payslips WHERE employee_id IN ({emp_placeholders})", emp_ids)
            payslip_ids = [row[0] for row in cursor.fetchall()]
            if payslip_ids:
                ps_placeholders = ','.join('?' for _ in payslip_ids)
                for table in ['payslip_earnings', 'payslip_deductions', 'payslip_employer_contributions', 'payslip_reimbursements']:
                    try:
                        cursor.execute(f"DELETE FROM {table} WHERE payslip_id IN ({ps_placeholders})", payslip_ids)
                    except sqlite3.OperationalError: pass
                cursor.execute(f"DELETE FROM payslips WHERE employee_id IN ({emp_placeholders})", emp_ids)

            # Other tables
            tables = ['attendance', 'employee_bank_details', 'employee_address', 'employee_documents', 'leaves', 'leave_balances']
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE employee_id IN ({emp_placeholders})", emp_ids)
                except sqlite3.OperationalError: pass

            # Unlink from departments/employees (as manager)
            try:
                cursor.execute(f"UPDATE departments SET manager_id = NULL WHERE manager_id IN ({emp_placeholders})", emp_ids)
                cursor.execute(f"UPDATE employees SET manager_id = NULL WHERE manager_id IN ({emp_placeholders})", emp_ids)
            except sqlite3.OperationalError: pass

            # Delete Employees
            cursor.execute(f"DELETE FROM employees WHERE id IN ({emp_placeholders})", emp_ids)
            print(f"   - Deleted {len(emp_ids)} employee records.")

        # 3. Delete Users
        cursor.execute(f"DELETE FROM user_permissions WHERE user_id IN ({placeholders})", manager_user_ids)
        cursor.execute(f"DELETE FROM users WHERE id IN ({placeholders})", manager_user_ids)
        print(f"   - Deleted {len(manager_user_ids)} user records.")

        conn.commit()
        print("\n✅ Successfully deleted all managers.")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    delete_managers()