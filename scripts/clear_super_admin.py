import sqlite3
import os

def clear_super_admin():
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
        # 1. Delete from super_admins table
        cursor.execute("DELETE FROM super_admins")
        print(f"✅ Deleted {cursor.rowcount} rows from 'super_admins'.")

        # 2. Delete from users table (only SUPER_ADMIN role)
        cursor.execute("DELETE FROM users WHERE role = 'SUPER_ADMIN'")
        print(f"✅ Deleted {cursor.rowcount} rows from 'users' (role='SUPER_ADMIN').")

        conn.commit()
        print("🚀 Super Admin data cleared successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clear_super_admin()