import sqlite3
import os

def add_reset_columns():
    db_path = os.path.join('instance', 'hrms.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking users table for reset_otp columns...")
    
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'reset_otp' not in columns:
            print("Adding reset_otp column...")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp VARCHAR(6)")
        else:
            print("reset_otp already exists.")

        if 'reset_otp_expiry' not in columns:
            print("Adding reset_otp_expiry column...")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_expiry DATETIME")
        else:
            print("reset_otp_expiry already exists.")
            
        conn.commit()
        print("✅ Database updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_reset_columns()