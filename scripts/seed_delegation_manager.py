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

def seed_delegations():
    with app.app_context():
        print("--- Seeding Delegations for Manager ---")
        
        # 1. Find a Manager and some team members
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ Error: No Manager user found.")
            return
            
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        others = Employee.query.filter(Employee.user_id != manager_user.id).limit(5).all()
        
        if not others:
            print("❌ Error: No other employees found to receive delegation.")
            return

        print(f"Manager: {manager_emp.full_name}")

        # 2. Delete existing delegations for this manager
        Delegation.query.filter_by(delegated_by_id=manager_emp.id).delete()

        # 3. Create 3 types of delegations
        
        # A. Active Delegation (Leave Approval)
        d1 = Delegation(
            company_id=manager_emp.company_id,
            delegated_by_id=manager_emp.id,
            delegated_to_id=others[0].id,
            module="Leave Approval",
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() + timedelta(days=5),
            notes="Delegating leave approvals while on vacation.",
            status="ACTIVE"
        )
        
        # B. Expired Delegation (Attendance Approval)
        d2 = Delegation(
            company_id=manager_emp.company_id,
            delegated_by_id=manager_emp.id,
            delegated_to_id=others[1].id,
            module="Attendance Approval",
            start_date=date.today() - timedelta(days=15),
            end_date=date.today() - timedelta(days=5),
            notes="Temporary delegation for last week's shift audit.",
            status="ACTIVE" # Logic in route handles displaying this as EXPIRED
        )
        
        # C. Active Delegation (All Modules)
        d3 = Delegation(
            company_id=manager_emp.company_id,
            delegated_by_id=manager_emp.id,
            delegated_to_id=others[2].id,
            module="All",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            notes="Short term full authority delegation.",
            status="ACTIVE"
        )

        db.session.add_all([d1, d2, d3])
        db.session.commit()
        print(f"✅ Successfully seeded delegations for {manager_emp.full_name}.")

if __name__ == "__main__":
    seed_delegations()
