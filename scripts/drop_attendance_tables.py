import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import text

def drop_attendance_tables():
    """
    Drops all tables related to the attendance module.
    This includes 'attendance', 'attendance_regularization', and the legacy 'attendance_logs'.
    """
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            print(f"❌ Database not found at {db_path}. Operation cancelled.")
            return

        print("Dropping attendance-related tables...")
        try:
            with db.engine.connect() as connection:
                transaction = connection.begin()
                
                # Drop tables. Order can matter if there are foreign keys.
                print("   - Dropping 'attendance_regularization'...")
                connection.execute(text("DROP TABLE IF EXISTS attendance_regularization;"))

                print("   - Dropping 'attendance'...")
                connection.execute(text("DROP TABLE IF EXISTS attendance;"))
                
                transaction.commit()
            print("✅ Attendance tables dropped successfully.")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    drop_attendance_tables()