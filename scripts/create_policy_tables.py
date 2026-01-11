import sys
import os
from sqlalchemy import inspect

# Add the parent directory to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
# Import the models so SQLAlchemy knows about them
import models.policy

def create_policy_tables():
    with app.app_context():
        print("Checking database for policy tables...")
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print(f"Existing tables: {existing_tables}")
        
        print("Running create_all() to add missing tables...")
        db.create_all()
        
        # Verify
        inspector = inspect(db.engine)
        new_tables = inspector.get_table_names()
        policy_tables = [t for t in new_tables if 'policy' in t]
        
        if policy_tables:
            print(f"✅ Successfully created policy tables: {policy_tables}")
        else:
            print("❌ Failed to create policy tables. Check model imports.")

if __name__ == "__main__":
    create_policy_tables()