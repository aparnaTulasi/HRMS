import sqlite3
import os

def update_schema():
    """
    Adds missing JSON columns to the employees table in the SQLite database.
    """
    # Get the absolute path to the database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'hrms.db')

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"🔌 Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # List of columns to ensure exist in 'employees' table
    # (Column Name, SQLite Type) - JSON is stored as TEXT in SQLite
    columns_to_check = [
        ('education_details', 'TEXT'),
        ('last_work_details', 'TEXT'),
        ('statutory_details', 'TEXT')
    ]

    print("🔍 Checking 'employees' table schema...")
    cursor.execute("PRAGMA table_info(employees)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    for col_name, col_type in columns_to_check:
        if col_name not in existing_columns:
            print(f"➕ Adding missing column: {col_name}")
            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
        else:
            print(f"✅ Column exists: {col_name}")

    conn.commit()
    conn.close()
    print("🎉 Schema update complete!")

if __name__ == "__main__":
    update_schema()