from app import app, db
from sqlalchemy import text

def add_shift_column():
    print("🔄 Adding 'shift_id' to attendance_logs table...")
    with app.app_context():
        with db.engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN shift_id INTEGER"))
                print("✅ Successfully added 'shift_id' column.")
                
                # Also add the foreign key constraint if it's MySQL (local usually is)
                # But safer to just add the column for now as simple SQLite/MySQL fix
                try:
                    conn.execute(text("ALTER TABLE attendance_logs ADD CONSTRAINT fk_attendance_shift FOREIGN KEY (shift_id) REFERENCES shifts(shift_id)"))
                    print("✅ Added foreign key constraint.")
                except Exception as fe:
                    print(f"ℹ️  Could not add foreign key constraint (might not be supported or already exists): {fe}")
                
                conn.commit()
            except Exception as e:
                print(f"❌ Error or column already exists: {e}")

if __name__ == "__main__":
    add_shift_column()
