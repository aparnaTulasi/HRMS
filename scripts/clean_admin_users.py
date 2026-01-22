import sqlite3
import os

def clean_admin_users():
    # Get the absolute path to the database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'hrms.db')

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"🔌 Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Find all ADMIN users
        cursor.execute("SELECT id FROM users WHERE role='ADMIN'")
        admin_rows = cursor.fetchall()
        admin_ids = [row[0] for row in admin_rows]

        if not admin_ids:
            print("ℹ️ No ADMIN users found to delete.")
            return

        print(f"found {len(admin_ids)} ADMIN users. Cleaning up...")

        # 2. Delete associated employees first (to maintain integrity)
        ids_placeholder = ','.join('?' for _ in admin_ids)
        
        print("🧹 Deleting associated records from 'employees' table...")
        cursor.execute(f"DELETE FROM employees WHERE user_id IN ({ids_placeholder})", admin_ids)

        # 3. Delete from users table
        print("🧹 Deleting records from 'users' table...")
        cursor.execute(f"DELETE FROM users WHERE id IN ({ids_placeholder})", admin_ids)
        
        conn.commit()
        print("✅ Admin users removed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_admin_users()