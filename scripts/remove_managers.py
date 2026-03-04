import sqlite3
import os

def remove_managers():
    """
    Connects to the database and deletes all users with the 'MANAGER' role,
    along with all their associated data in related tables.
    """
    # Get the absolute path to the database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'hrms.db')

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"🔌 Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    # Enable foreign key constraints to ensure data integrity
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        print("Finding users to delete (role = 'MANAGER')...")
        
        # 1. Get IDs of users to be deleted
        cursor.execute("SELECT id FROM users WHERE role = 'MANAGER'")
        user_ids_to_delete = [row[0] for row in cursor.fetchall()]
        
        if not user_ids_to_delete:
            print("✅ No users with role 'MANAGER' found to delete.")
            return

        print(f"Found {len(user_ids_to_delete)} manager(s) to delete.")
        
        user_id_placeholders = ','.join('?' for _ in user_ids_to_delete)

        # 2. Get IDs of corresponding employees
        cursor.execute(f"SELECT id FROM employees WHERE user_id IN ({user_id_placeholders})", user_ids_to_delete)
        employee_ids_to_delete = [row[0] for row in cursor.fetchall()]
        
        if employee_ids_to_delete:
            employee_id_placeholders = ','.join('?' for _ in employee_ids_to_delete)
            
            # 3. Handle Payslips (nested relationships)
            cursor.execute(f"SELECT id FROM payslips WHERE employee_id IN ({employee_id_placeholders})", employee_ids_to_delete)
            payslip_ids_to_delete = [row[0] for row in cursor.fetchall()]
            
            if payslip_ids_to_delete:
                payslip_id_placeholders = ','.join('?' for _ in payslip_ids_to_delete)
                payslip_child_tables = ['payslip_earnings', 'payslip_deductions', 'payslip_employer_contributions', 'payslip_reimbursements']
                for table in payslip_child_tables:
                    try:
                        cursor.execute(f"DELETE FROM {table} WHERE payslip_id IN ({payslip_id_placeholders})", payslip_ids_to_delete)
                    except sqlite3.OperationalError: pass
            
            # 4. Update manager references to NULL to avoid FK violations
            print("🧹 Nullifying manager references in 'employees' and 'departments' tables...")
            cursor.execute(f"UPDATE employees SET manager_id = NULL WHERE manager_id IN ({employee_id_placeholders})", employee_ids_to_delete)
            cursor.execute(f"UPDATE departments SET manager_id = NULL WHERE manager_id IN ({employee_id_placeholders})", employee_ids_to_delete)

            # 5. Delete from all other employee-related tables
            employee_child_tables = ['employee_address', 'employee_bank_details', 'employee_documents', 'attendance', 'leaves', 'leave_balances', 'payslips']
            for table in employee_child_tables:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE employee_id IN ({employee_id_placeholders})", employee_ids_to_delete)
                except sqlite3.OperationalError: pass

        # 6. Delete from employees table
        print("🧹 Deleting from 'employees'...")
        cursor.execute(f"DELETE FROM employees WHERE user_id IN ({user_id_placeholders})", user_ids_to_delete)
        
        # 7. Delete from user_permissions table
        print("🧹 Deleting from 'user_permissions'...")
        cursor.execute(f"DELETE FROM user_permissions WHERE user_id IN ({user_id_placeholders})", user_ids_to_delete)

        # 8. Finally, delete the users
        print("🧹 Deleting from 'users'...")
        cursor.execute(f"DELETE FROM users WHERE id IN ({user_id_placeholders})", user_ids_to_delete)

        conn.commit()
        print(f"\n✅ Successfully removed {len(user_ids_to_delete)} manager(s) and their related data.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("🔌 Database connection closed.")

if __name__ == "__main__":
    print("🚨 WARNING: This script will permanently delete all users with the 'MANAGER' role and their associated data.")
    confirm = input("Are you sure you want to continue? (yes/no): ")
    if confirm.lower() == 'yes':
        remove_managers()
    else:
        print("🚫 Operation cancelled.")