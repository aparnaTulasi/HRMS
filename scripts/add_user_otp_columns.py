import sqlite3
import os

def add_otp_columns():
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
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        # Add reset_otp
        if 'reset_otp' not in existing_columns:
            print("Adding column: reset_otp")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp TEXT")
        else:
            print("Column 'reset_otp' already exists.")

        # Add reset_otp_expiry
        if 'reset_otp_expiry' not in existing_columns:
            print("Adding column: reset_otp_expiry")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_expiry DATETIME")
        else:
            print("Column 'reset_otp_expiry' already exists.")

        conn.commit()
        print("✅ Users table updated successfully!")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_otp_columns()