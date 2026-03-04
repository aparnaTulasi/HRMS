import sqlite3
import os

def create_table():
    # Locate the database file
    db_path = os.path.join('instance', 'hrms.db')
    
    # Handle case where script is run from scripts/ folder
    if not os.path.exists(db_path):
        db_path = os.path.join('..', 'instance', 'hrms.db')

    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Creating super_admins table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS super_admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                email VARCHAR(120),
                password VARCHAR(255),
                confirm_password VARCHAR(255),
                reset_otp VARCHAR(10),
                reset_otp_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
        conn.commit()
        print("✅ super_admins table created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()