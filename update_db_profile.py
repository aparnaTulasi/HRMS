import sqlite3
import os

db_path = 'instance/hrms.db'
if not os.path.exists(db_path):
    # Try current directory
    db_path = 'hrms.db'

def update_db():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add columns to employees
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN bio TEXT")
            print("Added bio to employees")
        except sqlite3.OperationalError:
            print("bio already exists in employees")
            
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN emergency_contact VARCHAR(100)")
            print("Added emergency_contact to employees")
        except sqlite3.OperationalError:
            print("emergency_contact already exists in employees")

        # Add columns to super_admins
        try:
            cursor.execute("ALTER TABLE super_admins ADD COLUMN department VARCHAR(50) DEFAULT 'Management'")
            print("Added department to super_admins")
        except sqlite3.OperationalError:
            print("department already exists in super_admins")

        try:
            cursor.execute("ALTER TABLE super_admins ADD COLUMN bio TEXT")
            print("Added bio to super_admins")
        except sqlite3.OperationalError:
            print("bio already exists in super_admins")

        try:
            cursor.execute("ALTER TABLE super_admins ADD COLUMN emergency_contact VARCHAR(100)")
            print("Added emergency_contact to super_admins")
        except sqlite3.OperationalError:
            print("emergency_contact already exists in super_admins")

        try:
            cursor.execute("ALTER TABLE super_admins ADD COLUMN joining_date DATE")
            print("Added joining_date to super_admins")
        except sqlite3.OperationalError:
            print("joining_date already exists in super_admins")

        conn.commit()
        conn.close()
        print("Database update complete.")
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    update_db()
