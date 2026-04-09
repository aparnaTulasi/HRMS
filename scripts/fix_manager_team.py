import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee

def fix_team():
    with app.app_context():
        # 1. Find Manager
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ No Manager found.")
            return
            
        # 2. Find some employees who ARE NOT this manager
        others = Employee.query.filter(Employee.user_id != manager_user.id).limit(5).all()
        if not others:
            print("❌ No other employees found to assign.")
            return
            
        # 3. Assign them
        for emp in others:
            emp.manager_id = manager_user.id
            print(f"Assigned {emp.full_name} to Manager {manager_user.email}")
            
        db.session.commit()
        print("✅ Team setup complete.")

if __name__ == "__main__":
    fix_team()
