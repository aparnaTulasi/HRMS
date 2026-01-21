import sqlite3
import os

def add_reset_columns():
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
        print("⚠️ Adding 'reset_otp' column...")
        cursor.execute("ALTER TABLE super_admins ADD COLUMN reset_otp VARCHAR(6)")
        
        print("⚠️ Adding 'reset_otp_expiry' column...")
        cursor.execute("ALTER TABLE super_admins ADD COLUMN reset_otp_expiry DATETIME")

        conn.commit()
        print("✅ Database schema updated successfully!")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✅ Columns already exist. No changes needed.")
        else:
            print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_reset_columns()