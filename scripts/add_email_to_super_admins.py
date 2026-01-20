import sqlite3
import os

def add_email_column():
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

        # Add email column
        if 'email' not in existing_columns:
            print("Adding column: email")
            cursor.execute("ALTER TABLE super_admins ADD COLUMN email VARCHAR(120)")
            conn.commit()
            print("✅ 'email' column added to super_admins table.")
        else:
            print("✅ Column 'email' already exists in super_admins table.")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_email_column()