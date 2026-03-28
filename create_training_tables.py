import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def create_training_tables():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. training_programs
        print("Creating training_programs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                trainer_platform VARCHAR(150),
                start_date DATE NOT NULL,
                duration VARCHAR(50),
                training_hours INTEGER DEFAULT 0,
                description TEXT,
                status VARCHAR(30) DEFAULT 'Upcoming',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. training_participants
        print("Creating training_participants table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                training_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                completion_rate INTEGER DEFAULT 0,
                status VARCHAR(30) DEFAULT 'Joined',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (training_id) REFERENCES training_programs (id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        """)

        # 3. training_materials
        print("Creating training_materials table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                training_id INTEGER NOT NULL,
                title VARCHAR(150) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                file_type VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (training_id) REFERENCES training_programs (id) ON DELETE CASCADE
            )
        """)

        print("Training tables created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    create_training_tables()
