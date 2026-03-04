import sqlite3
import os

# Path to database
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(base_dir, "instance", "hrms.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at {DB_PATH}. Run 'python app.py' first to create it.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔄 Migrating 'employees' table...")
    
    # Columns to ensure exist in employees
    new_columns = {
        "full_name": "TEXT",
        "gender": "TEXT",
        "date_of_birth": "DATE",
        "department": "TEXT",
        "designation": "TEXT",
        "phone_number": "TEXT",
        "mobile_number": "TEXT",
        "ctc": "FLOAT",
        "pay_grade": "TEXT",
        "personal_email": "TEXT",
        "company_email": "TEXT",
        "aadhaar_number": "TEXT",
        "pan_number": "TEXT",
        "education_details": "TEXT",
        "last_work_details": "TEXT",
        "statutory_details": "TEXT",

    }

    # Get existing columns
    cursor.execute("PRAGMA table_info(employees)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    for col, dtype in new_columns.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE employees ADD COLUMN {col} {dtype}")
                print(f"   ✅ Added column: {col}")
            except Exception as e:
                print(f"   ⚠️ Could not add {col}: {e}")
    
    print("🔄 Migrating 'employee_address' table...")
    # Since employee_address changed structure significantly, we drop it to let Flask recreate it correctly
    try:
        cursor.execute("DROP TABLE IF EXISTS employee_address")
        print("   ✅ Dropped 'employee_address' table (will be recreated by app)")
    except Exception as e:
        print(f"   ⚠️ Error dropping employee_address: {e}")

    conn.commit()
    conn.close()
    print("✅ Migration complete. Now run 'python app.py'.")

if __name__ == "__main__":
    migrate()