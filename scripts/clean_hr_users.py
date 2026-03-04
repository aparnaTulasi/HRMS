import sys
import os

# Add the project root directory to Python path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db
from models.user import User
from models.employee import Employee

def clean_hr_users():
    """
    Deletes all users with role 'HR' and their associated employee records.
    """
    print("🚀 Starting HR User Cleanup...")
    
    with app.app_context():
        # 1. Find all HR users
        hr_users = User.query.filter_by(role='HR').all()
        
        if not hr_users:
            print("✅ No HR users found in the database.")
            return

        print(f"🔍 Found {len(hr_users)} HR users. Processing deletion...")

        for user in hr_users:
            Employee.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            print(f"   - Deleted: {user.email}")
        
        db.session.commit()
        print("✅ Cleanup complete.")

if __name__ == "__main__":
    clean_hr_users()