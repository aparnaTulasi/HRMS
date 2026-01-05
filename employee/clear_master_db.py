import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models.master import db, UserMaster, Company
from sqlalchemy import text

if __name__ == "__main__":
    with app.app_context():
        print("🧹 Cleaning up Master Database...")
        
        try:
            # Delete users first because of foreign key constraints (UserMaster -> Company)
            deleted_users = db.session.query(UserMaster).delete()
            print(f"   - Removed {deleted_users} users.")
            
            # Delete companies
            deleted_companies = db.session.query(Company).delete()
            print(f"   - Removed {deleted_companies} companies.")
            
            # Reset SQLite auto-increment sequences
            db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='companies'"))
            db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='users_master'"))
            
            db.session.commit()
            print("✅ Database is now empty.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing database: {e}")