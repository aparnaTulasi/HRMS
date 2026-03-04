import sqlite3
import os

def delete_employee_id_4():
    # Path to the database
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys to ensure constraints are respected (or handled manually below)
    cursor.execute("PRAGMA foreign_keys = ON;")

    target_emp_id = 4
    target_email_check = "aparna.futerinvo@gmail.com"
    
    print(f"🔄 Attempting to remove Employee ID: {target_emp_id}...")

    try:
        # 1. Check if employee exists and get User ID
        cursor.execute("SELECT id, user_id, full_name FROM employees WHERE id = ?", (target_emp_id,))
        emp = cursor.fetchone()
        
        if not emp:
            print(f"⚠️  Employee with ID {target_emp_id} not found in database.")
            return

        user_id = emp[1]
        full_name = emp[2]
        
        # Get user email for verification
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        email = user_row[0] if user_row else "Unknown"
        
        print(f"   Found: {full_name} (User ID: {user_id}, Email: {email})")
        
        if email.lower() != target_email_check.lower():
            print(f"⚠️  Warning: Email matches '{email}', expected '{target_email_check}'.")
        
        # 2. Delete related records in child tables
        print("   Deleting related records...")

        # List of tables that reference employee_id
        tables_referencing_employee = [
            'attendance', 
            'employee_bank_details', 
            'employee_address', 
            'employee_documents',
            'leaves',
            'leave_balances'
        ]

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
            print(f"   - Deleted {len(payslip_ids)} payslips and related components.")

        # Unlink as manager from departments
        try:
            cursor.execute("UPDATE departments SET manager_id = NULL WHERE manager_id = ?", (target_emp_id,))
        except sqlite3.OperationalError:
            pass

        # Delete from other tables
        for table in tables_referencing_employee:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE employee_id = ?", (target_emp_id,))
            except sqlite3.OperationalError:
                pass # Table might not exist

        # 3. Delete the Employee record
        cursor.execute("DELETE FROM employees WHERE id = ?", (target_emp_id,))
        print("   - Deleted from 'employees' table.")

        # 4. Unlink User from created/verified records (if they were HR/Admin)
        user_ref_updates = [
            ('pay_grades', 'created_by'),
            ('pay_roles', 'created_by'),
            ('payslips', 'created_by'),
            ('filter_configurations', 'created_by'),
            ('employee_documents', 'verified_by'),
            ('user_permissions', 'granted_by')
        ]
        for table, col in user_ref_updates:
            try:
                cursor.execute(f"UPDATE {table} SET {col} = NULL WHERE {col} = ?", (user_id,))
            except sqlite3.OperationalError:
                pass

        # 5. Delete the User record (and permissions)
        cursor.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        print("   - Deleted from 'users' table.")

        conn.commit()
        print(f"✅ Successfully removed Employee ID {target_emp_id} ({email}).")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    delete_employee_id_4()