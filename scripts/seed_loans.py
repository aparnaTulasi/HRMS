import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.loan import Loan
from app import app
from datetime import date, datetime, timedelta

def seed_loans():
    with app.app_context():
        db.create_all() # Ensure table exists
        
        company = Company.query.first()
        if not company:
            print("❌ No company found.")
            return
            
        employees = Employee.query.filter_by(company_id=company.id).all()
        if not employees:
            print("❌ No employees found.")
            return

        print(f"🌱 Seeding Loans for Company: {company.company_name}")
        
        today = date.today()
        
        # Add a few loans for the first few employees
        for i, emp in enumerate(employees[:2]):
            print(f"Loan seeding for {emp.full_name}...")
            
            loans_data = [
                {
                    "type": "Personal",
                    "amount": 50000.0,
                    "interest": 8.5,
                    "tenure": 12,
                    "status": "ACTIVE",
                    "disbursed": today - timedelta(days=60)
                },
                {
                    "type": "Home Renovation",
                    "amount": 150000.0,
                    "interest": 9.0,
                    "tenure": 24,
                    "status": "PENDING",
                    "disbursed": None
                }
            ]
            
            for ld in loans_data:
                # Simple EMI calc
                amt = ld['amount']
                intr = ld['interest']
                ten = ld['tenure']
                total_int = amt * (intr / 100) * (ten / 12)
                emi = (amt + total_int) / ten
                
                loan = Loan(
                    company_id=company.id,
                    employee_id=emp.id,
                    loan_type=ld['type'],
                    amount=amt,
                    interest_rate=intr,
                    tenure_months=ten,
                    emi=round(emi, 2),
                    status=ld['status'],
                    disbursement_date=ld['disbursed'],
                    reason=f"Financial assistance for {ld['type']}"
                )
                db.session.add(loan)
                
        db.session.commit()
        print("✅ Loan seeding completed successfully!")

if __name__ == "__main__":
    seed_loans()
