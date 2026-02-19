import sys
import os

# Add project root to python path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models.user import User
from models.super_admin import SuperAdmin

def clear_super_admin():
    with app.app_context():
        try:
            print("🔄 Connecting to database...")
            
            # 1. Delete SuperAdmin records
            deleted_sa = SuperAdmin.query.delete()
            print(f"✅ Deleted {deleted_sa} SuperAdmin profiles.")

            # 2. Delete User records with role SUPER_ADMIN
            deleted_users = User.query.filter_by(role='SUPER_ADMIN').delete()
            print(f"✅ Deleted {deleted_users} User accounts (SUPER_ADMIN).")

            db.session.commit()
            print("🎉 Super Admin data cleared successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing data: {e}")

if __name__ == "__main__":
    clear_super_admin()

    