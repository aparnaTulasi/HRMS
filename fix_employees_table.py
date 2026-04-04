from app import app, db
from sqlalchemy import text

def fix_employees_table():
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"))
            db.session.execute(text("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
            db.session.commit()
            print("Successfully updated employees table.")
        except Exception as e:
            print(f"Error updating table (columns might already exist): {e}")

if __name__ == "__main__":
    fix_employees_table()
