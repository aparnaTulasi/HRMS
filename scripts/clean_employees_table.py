import sqlite3
import os

def clean_employees_table():
    # Get the absolute path to the database
    # Assuming this script is in /scripts/ and db is in /instance/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'hrms.db')

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"🔌 Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # List of tables to clear (Child tables first to avoid FK issues)
        tables_to_clear = [
            'employee_address',
            'employee_bank_details',
            'employee_documents',
            'attendance',
            'leaves',
            'leave_balances',
            'payslip_earnings',
            'payslip_deductions',
            'payslip_employer_contributions',
            'payslip_reimbursements',
            'payslips',
            'employees'
        ]

        for table in tables_to_clear:
            try:
                print(f"🧹 Deleting from '{table}'...")
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            except sqlite3.OperationalError:
                pass # Table might not exist
        
        conn.commit()
        print("✅ Employees and related data cleaned successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_employees_table()