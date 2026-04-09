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
from models.loan import Loan

def seed_manager_loans():
    with app.app_context():
        print("--- Seeding Loans for Manager Team ---")
        
        # 1. Find a Manager and their Team
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ Error: No Manager user found. Please run main seeders first.")
            return
            
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        team_members = Employee.query.filter_by(manager_id=manager_user.id).all()
        
        if not team_members:
            print("❌ Error: Manager has no team members. Please assign some employees to this manager.")
            return

        print(f"Manager: {manager_emp.full_name} ({manager_user.email})")
        print(f"Team Size: {len(team_members)}")

        loan_types = ["Personal", "Home Renovation", "Emergency", "Education"]
        statuses = ["PENDING", "ACTIVE", "PAID", "REJECTED"]
        
        # 2. Delete existing loans for these team members to have a clean test
        team_ids = [e.id for e in team_members]
        Loan.query.filter(Loan.employee_id.in_(team_ids)).delete(synchronize_session=False)

        # 3. Create 10-15 random loans
        for _ in range(12):
            emp = random.choice(team_members)
            ltype = random.choice(loan_types)
            amount = random.randint(50000, 500000)
            tenure = random.choice([12, 24, 36, 48])
            interest = 8.5
            status = random.choice(statuses)
            
            # Simple EMI calculation: (P + (P*R*T/12)) / T
            total_interest = amount * (interest / 100) * (tenure / 12)
            emi = (amount + total_interest) / tenure

            loan = Loan(
                company_id=emp.company_id,
                employee_id=emp.id,
                loan_type=ltype,
                amount=float(amount),
                interest_rate=interest,
                tenure_months=tenure,
                emi=round(emi, 2),
                status=status,
                reason=f"Random {ltype} loan for testing dashboard.",
                disbursement_date=date.today() - timedelta(days=random.randint(0, 150)) if status in ["ACTIVE", "PAID"] else None
            )
            db.session.add(loan)

        db.session.commit()
        print(f"✅ Successfully seeded {Loan.query.filter(Loan.employee_id.in_(team_ids)).count()} loans for the manager's team.")

if __name__ == "__main__":
    seed_manager_loans()
