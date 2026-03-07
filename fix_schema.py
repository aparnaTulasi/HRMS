from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        # Check if branch_id column exists
        with db.engine.connect() as conn:
            # For MySQL
            result = conn.execute(text("SHOW COLUMNS FROM employees LIKE 'branch_id'"))
            if not result.fetchone():
                print("⌛ Adding branch_id column to employees table...")
                conn.execute(text("ALTER TABLE employees ADD COLUMN branch_id INTEGER"))
                conn.execute(text("ALTER TABLE employees ADD CONSTRAINT fk_employee_branch FOREIGN KEY (branch_id) REFERENCES branches(id)"))
                conn.commit()
                print("✅ branch_id column added successfully.")
            else:
                print("ℹ️ branch_id column already exists.")
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
