import sqlite3
import os

def delete_user_id_4():
    # Path to the database
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys to ensure constraints are respected
    cursor.execute("PRAGMA foreign_keys = ON;")

    target_user_id = 4
    
    print(f"🔄 Attempting to remove User ID: {target_user_id} and all associated data...")

    try:
        # 1. Check if user exists and get email
        cursor.execute("SELECT email FROM users WHERE id = ?", (target_user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            print(f"⚠️  User with ID {target_user_id} not found in database.")
            return

        email = user_row[0]
        print(f"   Found User: ID {target_user_id}, Email: {email}")
        
        # 2. Find associated employee record to clean up employee-specific data
        cursor.execute("SELECT id, full_name FROM employees WHERE user_id = ?", (target_user_id,))
        emp = cursor.fetchone()
        
        if emp:
            target_emp_id = emp[0]
            full_name = emp[1]
            print(f"   - User is associated with Employee ID: {target_emp_id} ({full_name})")
            print("   - Deleting related employee records...")

            # Handle Payslips specifically (nested relationships)
            cursor.execute("SELECT id FROM payslips WHERE employee_id = ?", (target_emp_id,))
            payslip_ids = [row[0] for row in cursor.fetchall()]
            if payslip_ids:
                ps_ids_str = ",".join(map(str, payslip_ids))
                for sub_table in ['payslip_earnings', 'payslip_deductions', 'payslip_employer_contributions', 'payslip_reimbursements']:
                    try:
                        cursor.execute(f"DELETE FROM {sub_table} WHERE payslip_id IN ({ps_ids_str})")
                    except sqlite3.OperationalError:
                        pass # Table might not exist yet
                cursor.execute(f"DELETE FROM payslips WHERE employee_id = ?", (target_emp_id,))
                print(f"     - Deleted {len(payslip_ids)} payslips and related components.")

            # Unlink as manager from departments and other employees
            try:
                cursor.execute("UPDATE departments SET manager_id = NULL WHERE manager_id = ?", (target_emp_id,))
                cursor.execute("UPDATE employees SET manager_id = NULL WHERE manager_id = ?", (target_emp_id,))
            except sqlite3.OperationalError:
                pass

            # Delete from other tables referencing employee_id
            for table in ['attendance', 'employee_bank_details', 'employee_address', 'employee_documents', 'leaves', 'leave_balances']:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE employee_id = ?", (target_emp_id,))
                except sqlite3.OperationalError:
                    pass # Table might not exist

            # Delete the Employee record
            cursor.execute("DELETE FROM employees WHERE id = ?", (target_emp_id,))
            print("     - Deleted from 'employees' table.")
        else:
            print("   - No associated employee record found for this user.")

        # 3. Unlink User from other records (e.g., created_by fields)
        print("   - Nullifying user references in other tables...")
        for table, col in [('pay_grades', 'created_by'), ('pay_roles', 'created_by'), ('payslips', 'created_by'), ('filter_configurations', 'created_by'), ('employee_documents', 'verified_by'), ('user_permissions', 'granted_by')]:
            try:
                cursor.execute(f"UPDATE {table} SET {col} = NULL WHERE {col} = ?", (target_user_id,))
            except sqlite3.OperationalError:
                pass # Table might not exist

        # 4. Delete the User's permissions
        print("   - Deleting from 'user_permissions' table...")
        try:
            cursor.execute("DELETE FROM user_permissions WHERE user_id = ?", (target_user_id,))
        except sqlite3.OperationalError:
            pass

        # 5. Delete the User record
        print("   - Deleting from 'users' table...")
        cursor.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
        
        conn.commit()
        print(f"\n✅ Successfully removed User ID {target_user_id} ({email}) and all associated data.")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("🔌 Database connection closed.")

if __name__ == "__main__":
    delete_user_id_4()
