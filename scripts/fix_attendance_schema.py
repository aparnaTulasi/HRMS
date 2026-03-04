from app import app
from models import db
from sqlalchemy import text

if __name__ == "__main__":
    with app.app_context():
        print("🛠️  Fixing Attendance Schema...")
        try:
            # Drop the table that has the wrong schema
            # We use raw SQL because SQLAlchemy might complain about missing columns if we try to use the Model to drop
            db.session.execute(text("DROP TABLE IF EXISTS attendance_logs"))
            db.session.commit()
            print("✅ Dropped old 'attendance_logs' table.")
            
            # Recreate it based on the current model
            db.create_all()
            print("✅ Recreated 'attendance_logs' table with correct columns.")
            
        except Exception as e:
            print(f"❌ Error: {e}")