from app import app, db
from models.attendance import Attendance
from sqlalchemy import text

def update_schema():
    print("🔄 Updating Attendance table schema...")
    with app.app_context():
        with db.engine.connect() as conn:
            # 1. Add 'year' column
            try:
                conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN year INTEGER"))
                print("✅ Added 'year' column.")
            except Exception as e:
                print(f"ℹ️  'year' column might already exist: {e}")
            
            # 2. Add 'month' column
            try:
                conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN month INTEGER"))
                print("✅ Added 'month' column.")
            except Exception as e:
                print(f"ℹ️  'month' column might already exist: {e}")

            # 3. Add 'remarks' column
            try:
                conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN remarks TEXT"))
                print("✅ Added 'remarks' column.")
            except Exception as e:
                print(f"ℹ️  'remarks' column might already exist: {e}")
            
            conn.commit()

        # 4. Backfill Data
        print("🔄 Backfilling year and month for existing records...")
        rows = Attendance.query.filter((Attendance.year == None) | (Attendance.month == None)).all()
        for row in rows:
            if row.attendance_date:
                row.year = row.attendance_date.year
                row.month = row.attendance_date.month
        
        db.session.commit()
        print(f"✅ Successfully updated {len(rows)} records.")

if __name__ == "__main__":
    update_schema()