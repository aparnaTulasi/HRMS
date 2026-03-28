import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def create_esign_tables():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. esign_requests
        print("Creating esign_requests table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS esign_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                letter_type VARCHAR(50) NOT NULL,
                sent_date DATE,
                due_date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'Pending',
                request_id INTEGER,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (request_id) REFERENCES letter_requests (id)
            )
        """)

        # 2. esign_settings
        print("Creating esign_settings table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS esign_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL UNIQUE,
                otp_enabled BOOLEAN DEFAULT 1,
                selfie_enabled BOOLEAN DEFAULT 0,
                aadhaar_enabled BOOLEAN DEFAULT 0,
                reminders_enabled BOOLEAN DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("E-Sign tables created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    create_esign_tables()
