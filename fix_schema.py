from app import app
from models import db
from sqlalchemy import text, inspect

def fix_attendance_regularization_schema():
    with app.app_context():
        # 1. Inspect existing columns
        inspector = inspect(db.engine)
        existing_cols = [c['name'] for c in inspector.get_columns('attendance_regularization')]
        print(f"Existing columns in 'attendance_regularization': {existing_cols}")

        queries = []

        # Add missing columns based on models/attendance.py
        if 'request_type' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN request_type VARCHAR(50)")
        if 'punch_type' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN punch_type VARCHAR(50)")
        if 'requested_punch_in' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN requested_punch_in DATETIME")
        if 'requested_punch_out' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN requested_punch_out DATETIME")
        if 'actual_time' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN actual_time VARCHAR(100)")
        if 'approver_comment' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN approver_comment TEXT")
        if 'approved_by' not in existing_cols:
            queries.append("ALTER TABLE attendance_regularization ADD COLUMN approved_by INT")

        # Optional: Handle deprecated/differently named columns from models/regularization.py
        # If we have data in requested_login_at we might want to copy it, but table is empty.
        
        # Execute queries
        for q in queries:
            print(f"Executing: {q}")
            try:
                db.session.execute(text(q))
                db.session.commit()
            except Exception as e:
                print(f"Error executing {q}: {e}")
                db.session.rollback()

        # 2. Add Foreign Key for approved_by if possible
        try:
            db.session.execute(text("ALTER TABLE attendance_regularization ADD CONSTRAINT fk_approved_by FOREIGN KEY (approved_by) REFERENCES users(id)"))
            db.session.commit()
        except Exception as e:
            print(f"Error adding FK (might already exist): {e}")
            db.session.rollback()

        # 3. Drop redundant plural table if it exists
        try:
            if 'attendance_regularizations' in inspector.get_table_names():
                print("Dropping redundant table 'attendance_regularizations'")
                db.session.execute(text("DROP TABLE attendance_regularizations"))
                db.session.commit()
        except Exception as e:
            print(f"Error dropping table: {e}")
            db.session.rollback()

        print("Schema fix completed!")

if __name__ == "__main__":
    fix_attendance_regularization_schema()
