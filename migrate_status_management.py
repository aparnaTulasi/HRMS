import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    # Database connection parameters
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'hrms_db',
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            print("Starting migration for status management columns...")

            # 1. Update Employees table
            try:
                cursor.execute("ALTER TABLE employees ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'")
                cursor.execute("ALTER TABLE employees ADD COLUMN is_active TINYINT(1) DEFAULT 1")
                print("Added status and is_active to employees table.")
            except Exception as e:
                print(f"Error updating employees table: {e}")

            # 2. Update Departments table
            try:
                cursor.execute("ALTER TABLE departments ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'")
                print("Added status to departments table.")
            except Exception as e:
                print(f"Error updating departments table: {e}")

            # 3. Update Job Postings table (add is_active for unified toggle)
            try:
                cursor.execute("ALTER TABLE job_postings ADD COLUMN is_active TINYINT(1) DEFAULT 1")
                print("Added is_active to job_postings table.")
            except Exception as e:
                print(f"Error updating job_postings table: {e}")

            # 4. Update Users table (ensure is_active exists if not there)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1")
                print("Added is_active to users table.")
            except Exception as e:
                print(f"Error updating users table (might already exist): {e}")

            connection.commit()
            print("Migration completed successfully!")

    finally:
        connection.close()

if __name__ == "__main__":
    migrate()
