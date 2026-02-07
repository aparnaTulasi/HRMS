import sqlite3

DB_PATH = "instance/hrms.db"   # update only if your db path is different

# Columns your current Employee model expects (from your error)
COLUMNS_TO_ADD = [
    ("manager_id", "INTEGER"),
    ("employment_type", "TEXT"),
    ("salary", "REAL"),
    ("company_email", "TEXT"),
    ("work_mode", "TEXT"),
    ("branch_id", "INTEGER"),
    ("education_details", "TEXT"),
    ("last_work_details", "TEXT"),
    ("statutory_details", "TEXT"),
    ("father_or_husband_name", "TEXT"),
    ("mother_name", "TEXT"),
    ("company_code", "TEXT"),
]

def get_existing_columns(cur):
    cur.execute("PRAGMA table_info(employees);")
    return {row[1] for row in cur.fetchall()}  # row[1] = column name

def main():
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
