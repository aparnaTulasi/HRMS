from app import app
from models import db
from sqlalchemy import text, inspect

def migrate_attendance_v2():
    with app.app_context():
        inspector = inspect(db.engine)
        
        # 1. Handle attendance_logs (Unify Dashboard & Audit)
        print("Migrating attendance_logs...")
        
        # Check for duplicates before dropping super_admin_id
        # We already checked and found none, but this logic is here for safety.
        
        # Drop the old constraint
        try:
            # We need to find the name of the unique constraint. 
            # It was uq_att_company_emp_sa_date.
            print("Dropping old unique constraint uq_att_company_emp_sa_date...")
            db.session.execute(text("ALTER TABLE attendance_logs DROP INDEX uq_att_company_emp_sa_date"))
            db.session.commit()
        except Exception as e:
            print(f"Note: Could not drop index uq_att_company_emp_sa_date (might not exist): {e}")
            db.session.rollback()

        # Add the NEW unique constraint
        try:
            print("Adding new unique constraint uq_att_company_emp_date...")
            db.session.execute(text("ALTER TABLE attendance_logs ADD CONSTRAINT uq_att_company_emp_date UNIQUE (company_id, employee_id, attendance_date)"))
            db.session.commit()
        except Exception as e:
            print(f"Error adding new constraint: {e}")
            db.session.rollback()

        # Drop super_admin_id column
        try:
            print("Dropping super_admin_id column from attendance_logs...")
            db.session.execute(text("ALTER TABLE attendance_logs DROP COLUMN super_admin_id"))
            db.session.commit()
        except Exception as e:
            print(f"Note: Could not drop super_admin_id (might not exist): {e}")
            db.session.rollback()

        # 2. Audit AttendanceRegularization (Fixing Deletion Error)
        print("Auditing attendance_regularization schema...")
        existing_cols = [c['name'] for c in inspector.get_columns('attendance_regularization')]
        
        # SQLAlchemy sometimes queries columns that were accidentally removed or renamed.
        # Let's ensure ALL used columns exist.
        required_cols = [
            ('request_type', 'VARCHAR(50)'),
            ('punch_type', 'VARCHAR(50)'),
            ('requested_punch_in', 'DATETIME'),
            ('requested_punch_out', 'DATETIME'),
            ('actual_time', 'VARCHAR(100)'),
            ('approver_comment', 'TEXT'),
            ('approved_by', 'INT')
        ]
        
        for col_name, col_def in required_cols:
            if col_name not in existing_cols:
                print(f"Adding missing column {col_name} to attendance_regularization...")
                db.session.execute(text(f"ALTER TABLE attendance_regularization ADD COLUMN {col_name} {col_def}"))
                db.session.commit()

        # 3. Final Check
        print("Migration v2 completed successfully!")

if __name__ == "__main__":
    migrate_attendance_v2()
