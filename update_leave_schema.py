from app import app
from models import db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        try:
            # Check if columns exist
            with db.engine.connect() as conn:
                # Add columns
                try:
                    conn.execute(text("ALTER TABLE leave_requests ADD COLUMN is_half_day BOOLEAN DEFAULT 0"))
                    print("Added is_half_day column")
                except Exception as e:
                    print(f"is_half_day might already exist: {e}")
                
                try:
                    conn.execute(text("ALTER TABLE leave_requests ADD COLUMN attachment_url VARCHAR(255)"))
                    print("Added attachment_url column")
                except Exception as e:
                    print(f"attachment_url might already exist: {e}")
                
                conn.commit()
            print("Schema update attempt finished.")
        except Exception as e:
            print(f"Fatal error updating schema: {e}")

if __name__ == "__main__":
    update_schema()
