import sys
import os
from sqlalchemy import text

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db

def migrate():
    with app.app_context():
        print("Starting migration...")
        
        # Add columns one by one without IF NOT EXISTS for compatibility
        columns_to_add = [
            "ALTER TABLE users ADD COLUMN profile_completed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN profile_locked BOOLEAN DEFAULT FALSE"
        ]
        
        for sql in columns_to_add:
            try:
                db.session.execute(text(sql))
                db.session.commit()
                print(f"Executed: {sql}")
            except Exception as e:
                db.session.rollback()
                if "Duplicate column name" in str(e):
                    print(f"Column already exists: {sql.split()[-4]}")
                else:
                    print(f"Error executing {sql}: {e}")

if __name__ == "__main__":
    migrate()
