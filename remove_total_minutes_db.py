from app import app, db
from sqlalchemy import text

def remove_column():
    print("🔄 Removing 'total_minutes' column from attendance_logs...")
    with app.app_context():
        with db.engine.connect() as conn:
            try:
                # SQLite >= 3.35.0 supports DROP COLUMN
                conn.execute(text("ALTER TABLE attendance_logs DROP COLUMN total_minutes"))
                print("✅ Column 'total_minutes' dropped successfully.")
            except Exception as e:
                print(f"⚠️  Error dropping column (might be old SQLite): {e}")
                print("ℹ️  If this fails, you may need to recreate the table or ignore the extra column.")
            
            conn.commit()

if __name__ == "__main__":
    remove_column()