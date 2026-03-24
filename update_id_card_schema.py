import sqlite3
import os

db_path = os.path.join('instance', 'hrms.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE id_cards ADD COLUMN company_logo_url TEXT")
        print("Added company_logo_url")
    except Exception as e:
        print(f"Skipping company_logo_url: {e}")

    try:
        cursor.execute("ALTER TABLE id_cards ADD COLUMN emergency_contact TEXT")
        print("Added emergency_contact")
    except Exception as e:
        print(f"Skipping emergency_contact: {e}")

    conn.commit()
    conn.close()
    print("ID Card schema updated successfully.")
else:
    print("Database file not found. create_all() will handle it if the table doesn't exist.")
