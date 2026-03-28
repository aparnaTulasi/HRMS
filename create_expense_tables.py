import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def create_expense_tables():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. expense_claims table
        print("Creating expense_claims table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                project_purpose VARCHAR(255) NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount FLOAT NOT NULL,
                currency VARCHAR(10) DEFAULT '$',
                expense_date DATE NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'PENDING',
                year INTEGER,
                month INTEGER,
                day INTEGER,
                time VARCHAR(20),
                added_by_name VARCHAR(150),
                approved_by INTEGER,
                approved_at DATETIME,
                rejection_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (approved_by) REFERENCES employees (id)
            )
        """)

        print("Expenses table created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    create_expense_tables()
