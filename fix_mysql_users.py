import mysql.connector
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

def fix_mysql():
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "hrms_db")

    print(f"Connecting to MySQL: {db_name} at {db_host}...")
    
    try:
        conn = mysql.connector.connect(
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name
        )
        cursor = conn.cursor()

        # 1. Add last_login to users if missing
        print("Checking for last_login column in users table...")
        cursor.execute("SHOW COLUMNS FROM users LIKE 'last_login'")
        if not cursor.fetchone():
            print("Adding last_login column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME NULL AFTER otp_expiry")
        else:
            print("last_login column already exists.")

        # 2. Add other missing columns for User model flags I saw (profile_completed, profile_locked, portal_prefix, etc.)
        # Based on models/user.py
        cols_to_add = [
            ("profile_completed", "TINYINT(1) DEFAULT 0"),
            ("profile_locked", "TINYINT(1) DEFAULT 0"),
            ("portal_prefix", "VARCHAR(50) NULL"),
            ("otp", "VARCHAR(6) NULL"),
            ("otp_expiry", "DATETIME NULL")
        ]
        
        for col, col_type in cols_to_add:
            cursor.execute(f"SHOW COLUMNS FROM users LIKE '{col}'")
            if not cursor.fetchone():
                print(f"Adding {col} column to users table...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ MySQL User table fixed.")

    except Exception as e:
        print(f"❌ Error fixing MySQL: {e}")

if __name__ == "__main__":
    fix_mysql()
