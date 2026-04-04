from app import app, db
from sqlalchemy import text

def fix_permissions_table():
    with app.app_context():
        try:
            # Check if columns exist or just try adding them
            db.session.execute(text("ALTER TABLE user_permissions ADD COLUMN granted_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            db.session.execute(text("ALTER TABLE user_permissions ADD COLUMN granted_by INT"))
            db.session.commit()
            print("Successfully updated user_permissions table.")
        except Exception as e:
            print(f"Error updating table (columns might already exist): {e}")

if __name__ == "__main__":
    fix_permissions_table()
