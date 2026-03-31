from app import app
from models import db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Starting migration for status management columns...")

        # 1. Update Employees table
        try:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"))
            db.session.commit()
            print("Added status to employees table.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding status to employees: {e}")

        try:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN is_active TINYINT(1) DEFAULT 1"))
            db.session.commit()
            print("Added is_active to employees table.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding is_active to employees: {e}")

        # 2. Update Departments table
        try:
            db.session.execute(text("ALTER TABLE departments ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"))
            db.session.commit()
            print("Added status to departments table.")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating departments table: {e}")

        # 3. Update Job Postings table
        try:
            db.session.execute(text("ALTER TABLE job_postings ADD COLUMN is_active TINYINT(1) DEFAULT 1"))
            db.session.commit()
            print("Added is_active to job_postings table.")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating job_postings table: {e}")

        # 4. Update Users table
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1"))
            db.session.commit()
            print("Added is_active to users table.")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating users table (might already exist): {e}")

        print("Migration completed!")

if __name__ == "__main__":
    migrate()
