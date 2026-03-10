from app import app, db
from sqlalchemy import text

def fix_attendance_schema():
    print("🔄 Fixing Attendance table schema...")
    with app.app_context():
        with db.engine.connect() as conn:
            # 1. Add 'super_admin_id'
            try:
                conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN super_admin_id INTEGER"))
                print("✅ Added 'super_admin_id' column.")
            except Exception as e:
                print(f"ℹ️  'super_admin_id' column might already exist: {e}")

            # 2. Add FK for super_admin_id
            try:
                conn.execute(text("ALTER TABLE attendance_logs ADD CONSTRAINT fk_att_super_admin FOREIGN KEY (super_admin_id) REFERENCES super_admins(id)"))
                print("✅ Added foreign key for super_admin_id.")
            except Exception as e:
                print(f"ℹ️  Could not add FK for super_admin_id: {e}")

            conn.commit()

if __name__ == "__main__":
    fix_attendance_schema()
