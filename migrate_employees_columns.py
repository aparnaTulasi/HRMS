import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "hrms.db")

# Columns your current Employee model expects (from your error)
COLUMNS_TO_ADD = [
    ("department", "TEXT"),
    ("designation", "TEXT"),
    ("company_email", "TEXT"),
    ("education_details", "TEXT"),
    ("last_work_details", "TEXT"),
    ("statutory_details", "TEXT"),
    ("full_name", "TEXT"),
    ("gender", "TEXT"),
    ("date_of_birth", "DATE"),
    ("phone_number", "TEXT"),
    ("personal_email", "TEXT"),
    ("mobile_number", "TEXT"),
    ("ctc", "REAL"),
    ("pay_grade", "TEXT"),
]

def get_existing_columns(cur):
    cur.execute("PRAGMA table_info(employees);")
    return {row[1] for row in cur.fetchall()}  # row[1] = column name

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    existing = get_existing_columns(cur)
    added = []

    for col, col_type in COLUMNS_TO_ADD:
        if col not in existing:
            sql = f"ALTER TABLE employees ADD COLUMN {col} {col_type};"
            cur.execute(sql)
            added.append(col)

    conn.commit()
    conn.close()

    if added:
        print("✅ Added columns:", ", ".join(added))
    else:
        print("✅ No missing columns. DB already up to date.")

if __name__ == "__main__":
    main()
