import sqlite3
import os

def reset_super_admin():
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
        # 1. Clean up Users table (Remove existing Super Admins to prevent duplicate email errors)
        print("🧹 Cleaning up old Super Admin users...")
        cursor.execute("DELETE FROM users WHERE role = 'SUPER_ADMIN'")
        
        # 2. Drop old SuperAdmin table
        print("⚠️ Dropping old 'super_admins' table...")
        cursor.execute("DROP TABLE IF EXISTS super_admins")

        # 3. Recreate SuperAdmin table with NEW Schema (user_id + reset_otp)
        print("🔨 Creating new 'super_admins' table...")
        cursor.execute("""
            CREATE TABLE super_admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                email VARCHAR(120) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                is_verified BOOLEAN DEFAULT 0,
                signup_otp VARCHAR(6),
                signup_otp_expiry DATETIME,
                reset_otp VARCHAR(6),
                reset_otp_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        print("✅ Super Admin system reset successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_super_admin()