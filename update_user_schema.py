import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'instance', 'hrms.db')

def update_schema():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add last_login to users
        print("Adding last_login to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
        print("Column added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column last_login already exists.")
        else:
            print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    update_schema()
