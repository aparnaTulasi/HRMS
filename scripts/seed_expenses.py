import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.expense import ExpenseClaim
from app import app
from datetime import date, datetime, timedelta

def seed_expenses():
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

        print(f"🌱 Seeding Expenses for Company: {company.company_name}")
        
        today = date.today()
        now_time = datetime.now().strftime("%H:%M:%S")
        
        categories = ["Flight", "Hotel", "Taxi", "Meals"]
        statuses = ["APPROVED", "PENDING", "APPROVED", "REJECTED"]
        
        # Add a few expenses for the first few employees
        for i, emp in enumerate(employees[:2]):
            print(f"Expense seeding for {emp.full_name}...")
            
            # Seed across different months to show trend
            for m_offset in range(4):
                expense_date = today - timedelta(days=m_offset*30)
                
                claim = ExpenseClaim(
                    company_id=company.id,
                    employee_id=emp.id,
                    project_purpose=f"Client Meeting {m_offset+1}",
                    category=categories[m_offset % len(categories)],
                    amount=150.0 + (m_offset * 50),
                    currency="$",
                    expense_date=expense_date,
                    description=f"Travel for project work in month {expense_date.month}",
                    status=statuses[m_offset % len(statuses)],
                    
                    # Detailed fields
                    year=expense_date.year,
                    month=expense_date.month,
                    day=expense_date.day,
                    time=now_time,
                    added_by_name=emp.full_name
                )
                db.session.add(claim)
                
        db.session.commit()
        print("✅ Expense seeding completed successfully!")

if __name__ == "__main__":
    seed_expenses()
