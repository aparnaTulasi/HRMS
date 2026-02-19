import sys
import os

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
# Import all models to ensure they are registered
from models.user import User
from models.company import Company
from models.employee import Employee
from models.super_admin import SuperAdmin
from models.department import Department
from models.designation import Designation
from models.user_permission import UserPermission
from models.bank_details import BankDetails

def reset_database():
    with app.app_context():
        print("⚠️  WARNING: This will delete all data in the database!")
        print("🔄 Dropping all tables...")
        db.drop_all()
        print("✨ Creating all tables with new schema...")
        db.create_all()
        print("✅ Database reset successfully.")

if __name__ == "__main__":
    reset_database()