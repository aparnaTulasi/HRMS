import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def create_loan_tables():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. loans table
        print("Creating loans table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                loan_type VARCHAR(50) NOT NULL,
                amount FLOAT NOT NULL,
                interest_rate FLOAT DEFAULT 8.5,
                tenure_months INTEGER NOT NULL,
                emi FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                disbursement_date DATE,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        """)

        print("Loans table created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    create_loan_tables()
