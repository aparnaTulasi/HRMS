import sqlite3
import os

# Path to database
DB_PATH = os.path.join("instance", "hrms.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found. Run 'python app.py' first to create it.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔄 Migrating 'employees' table...")
    
    # Columns to ensure exist in employees
    new_columns = {
        "father_or_husband_name": "TEXT",
        "mother_name": "TEXT",
        "personal_email": "TEXT",
        "personal_mobile": "TEXT",
        "company_email": "TEXT",
        "work_phone": "TEXT",
        "work_mode": "TEXT",
        "branch_id": "INTEGER",
        "aadhaar_number": "TEXT",
        "pan_number": "TEXT",
        "salary": "FLOAT"
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