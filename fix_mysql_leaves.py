import mysql.connector
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

def fix_mysql_leaves():
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

        # 1. Fix leave_types
        print("Checking for 'code' in leave_types...")
        cursor.execute("SHOW COLUMNS FROM leave_types LIKE 'code'")
        if not cursor.fetchone():
            print("Adding 'code' column to leave_types...")
            cursor.execute("ALTER TABLE leave_types ADD COLUMN code VARCHAR(20) NULL AFTER company_id")
        
        # 2. Fix leave_requests
        print("Checking for new columns in leave_requests...")
        cols_to_add = [
            ("is_half_day", "TINYINT(1) DEFAULT 0"),
            ("attachment_url", "VARCHAR(255) NULL")
        ]
        for col, col_type in cols_to_add:
            cursor.execute(f"SHOW COLUMNS FROM leave_requests LIKE '{col}'")
            if not cursor.fetchone():
                print(f"Adding {col} to leave_requests...")
                cursor.execute(f"ALTER TABLE leave_requests ADD COLUMN {col} {col_type}")

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ MySQL Leave tables fixed.")

    except Exception as e:
        print(f"❌ Error fixing MySQL Leaves: {e}")

if __name__ == "__main__":
    fix_mysql_leaves()
