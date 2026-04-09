import sys
import os
import random
from datetime import datetime, date, timedelta

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.delegation import Delegation

def seed_delegations_full():
    with app.app_context():
        print("--- Seeding Full Delegation Data ---")
        
        # 1. Setup Manager and Team
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ No manager found.")
            return
            
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        others = Employee.query.filter(Employee.user_id != manager_user.id).limit(5).all()

        # 2. Setup Team (Required for Enforcement Testing)
        for emp in others[:3]:
            emp.manager_id = manager_user.id
            print(f"Assigned {emp.full_name} to Manager {manager_user.email}")
        
        # 3. Create Delegations
        # A. Active Leave Delegation
        d1 = Delegation(
            company_id=manager_emp.company_id,
            delegated_by_id=manager_emp.id,
            delegated_to_id=others[3].id,
            module="Leave Approval",
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=7),
            notes="Active Leave Delegation for Testing",
            status="ACTIVE"
        )
        
        # B. Active Attendance Delegation
        d2 = Delegation(
            company_id=manager_emp.company_id,
            delegated_by_id=manager_emp.id,
            delegated_to_id=others[4].id,
            module="Attendance Approval",
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=7),
            notes="Active Attendance Delegation for Testing",
            status="ACTIVE"
        )
        
        # C. Expired Delegation
        d3 = Delegation(
            company_id=manager_emp.company_id,
            delegated_by_id=manager_emp.id,
            delegated_to_id=others[0].id,
            module="All",
            start_date=date.today() - timedelta(days=20),
            end_date=date.today() - timedelta(days=10),
            notes="Expired Record",
            status="ACTIVE"
        )

        db.session.add_all([d1, d2, d3])
        db.session.commit()
        print("✅ Full delegation seeding complete.")

if __name__ == "__main__":
    seed_delegations_full()
