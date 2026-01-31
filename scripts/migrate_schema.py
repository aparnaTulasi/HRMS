import sqlite3
import os

DB_PATH = os.path.join("instance", "hrms.db")

def run_migration():
    if not os.path.exists(DB_PATH):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Rebuilding 'attendance_logs' table...")
    # Drop old attendance table to recreate with new schema
    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS attendance_logs")
    
    # Create new attendance table
    cursor.execute("""
    CREATE TABLE attendance_logs (
        attendance_id INTEGER PRIMARY KEY,
        employee_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        date DATE NOT NULL,
        punch_in_time DATETIME,
        punch_out_time DATETIME,
        total_hours FLOAT,
        location VARCHAR(200),
        capture_method VARCHAR(50) DEFAULT 'Web',
        status VARCHAR(20) DEFAULT 'Present',
        regularization_status VARCHAR(20) DEFAULT 'N/A',
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(employee_id) REFERENCES employees(id),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    print("   ✅ Created 'attendance_logs' table")

    print("🔄 Dropping Shift and Regularization tables if exist...")
    cursor.execute("DROP TABLE IF EXISTS shift")
    cursor.execute("DROP TABLE IF EXISTS shift_assignment")
    cursor.execute("DROP TABLE IF EXISTS regularization_requests")

    print("🔄 Rebuilding Leave tables...")
    cursor.execute("DROP TABLE IF EXISTS leaves") # Old table
    cursor.execute("DROP TABLE IF EXISTS leave_requests") # New table
    cursor.execute("DROP TABLE IF EXISTS leave_balances")
    cursor.execute("DROP TABLE IF EXISTS leave_types")
    
    print("🔄 Dropping Task tables if exist...")
    cursor.execute("DROP TABLE IF EXISTS daily_tasks")
    cursor.execute("DROP TABLE IF EXISTS tasks")

    print("🔄 Dropping other new tables if exist...")
    cursor.execute("DROP TABLE IF EXISTS payslips")
    cursor.execute("DROP TABLE IF EXISTS assets")
    cursor.execute("DROP TABLE IF EXISTS asset_allocations")
    cursor.execute("DROP TABLE IF EXISTS travel_expenses")
    cursor.execute("DROP TABLE IF EXISTS employee_bank_details")
    
    print("🔄 Dropping Payroll tables if exist...")
    cursor.execute("DROP TABLE IF EXISTS employee_salary_structure")
    cursor.execute("DROP TABLE IF EXISTS salary_structure_components")
    cursor.execute("DROP TABLE IF EXISTS salary_structures")
    cursor.execute("DROP TABLE IF EXISTS salary_components")
    cursor.execute("DROP TABLE IF EXISTS payroll_summary")
    cursor.execute("DROP TABLE IF EXISTS payroll_deductions")
    cursor.execute("DROP TABLE IF EXISTS payroll_earnings")
    cursor.execute("DROP TABLE IF EXISTS payroll_run_employees")
    cursor.execute("DROP TABLE IF EXISTS payroll_run")

    conn.commit()
    conn.close()
    print("✅ Schema cleanup complete.")
    print("👉 Now run 'python app.py' to create the new tables.")

if __name__ == "__main__":
    run_migration()