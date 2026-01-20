import sqlite3
import os

def add_columns():
    # Path to database
    db_path = os.path.join('instance', 'hrms.db')
    
    # Adjust path if running from scripts directory
    if not os.path.exists(db_path):
        db_path = os.path.join('..', 'instance', 'hrms.db')
        
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"Connecting to: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(super_admins)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        # Add password
        if 'password' not in existing_columns:
            print("Adding column: password")
            cursor.execute("ALTER TABLE super_admins ADD COLUMN password VARCHAR(255)")
        else:
            print("Column 'password' already exists.")

        # Add confirm_password
        if 'confirm_password' not in existing_columns:
            print("Adding column: confirm_password")
            cursor.execute("ALTER TABLE super_admins ADD COLUMN confirm_password VARCHAR(255)")
        else:
            print("Column 'confirm_password' already exists.")

        conn.commit()
        print("✅ super_admins table updated successfully!")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_columns()