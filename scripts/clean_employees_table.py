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
        # 1. Delete all data from employees table
        print("🧹 Deleting all records from 'employees' table...")
        cursor.execute("DELETE FROM employees")
        
        # 2. Reset the auto-increment ID
        print("🔄 Resetting 'employees' ID sequence...")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='employees'")
        
        conn.commit()
        print("✅ Employees table cleaned successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_employees_table()