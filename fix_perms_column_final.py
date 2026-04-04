from app import app, db
from sqlalchemy import text

def fix_perms_column():
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE user_permissions CHANGE COLUMN permission permission_code VARCHAR(50)"))
            db.session.commit()
            print("Successfully renamed permission to permission_code in user_permissions table.")
        except Exception as e:
            print(f"Error renaming column (it might already be permission_code): {e}")

if __name__ == "__main__":
    fix_perms_column()
