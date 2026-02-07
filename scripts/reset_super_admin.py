import sqlite3
import os

def clean_super_admin_data():
    # Determine DB path relative to this script
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Delete from super_admins table (Child)
        print("🧹 Deleting data from 'super_admins' table...")
        try:
            cursor.execute("DELETE FROM super_admins")
            sa_deleted = cursor.rowcount
            print(f"   - Deleted {sa_deleted} rows from 'super_admins' table.")
        except sqlite3.OperationalError:
            print("   - 'super_admins' table does not exist (skipping).")

        # 2. Delete Super Admin Users (Parent)
        print("🧹 Deleting users with role 'SUPER_ADMIN'...")
        cursor.execute("DELETE FROM users WHERE role = 'SUPER_ADMIN'")
        users_deleted = cursor.rowcount
        print(f"   - Deleted {users_deleted} rows from 'users' table.")

        conn.commit()
        print("✅ Super Admin data removed successfully.")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_super_admin_data()