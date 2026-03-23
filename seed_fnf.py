import sys
import os
from datetime import datetime, date

# Add the project root to the python path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.employee import Employee
from models.employee_statutory import FullAndFinal

def seed_fnf():
    with app.app_context():
        # Get first few employees
        employees = Employee.query.limit(3).all()
        if not employees:
            print("No employees found to seed F&F data")
            return

        # Seed data for first employee
        emp1 = employees[0]
        fnf1 = FullAndFinal.query.filter_by(employee_id=emp1.id).first()
        if not fnf1:
            fnf1 = FullAndFinal(
                employee_id=emp1.id,
                company_id=emp1.company_id,
                resign_date=date(2025, 6, 1),
                last_working_day=date(2025, 6, 30),
                notice_period_required=60,
                notice_period_served=60,
                notice_status='Served',
                status='Processing',
                settlement_data={
                    "salaryForLastMonth": 52000,
                    "leaveEncashment": 24000,
                    "pendingLeaves": 9,
                    "gratuity": 138462,
                    "noticePeriodPayIn": 0,
                    "bonusDues": 15000,
                    "expenseReimbursement": 5500,
                    "noticePeriodRecovery": 0,
                    "loanRecovery": 12000,
                    "pfEmployee": 57600,
                    "pfEmployer": 57600,
                    "pfTotal": 115200,
                    "gratuityTaxExempt": 138462,
                    "tdsOnSettlement": 4500,
                    "assetRecovery": 0
                },
                exit_clearance=[
                    {"dept": "IT Department", "item": "Laptop returned", "done": True},
                    {"dept": "HR Department", "item": "Exit interview", "done": True}
                ]
            )
            db.session.add(fnf1)
            print(f"Seeded F&F for {emp1.full_name}")

        # Seed data for second employee
        if len(employees) > 1:
            emp2 = employees[1]
            fnf2 = FullAndFinal.query.filter_by(employee_id=emp2.id).first()
            if not fnf2:
                fnf2 = FullAndFinal(
                    employee_id=emp2.id,
                    company_id=emp2.company_id,
                    resign_date=date(2026, 1, 15),
                    last_working_day=date(2026, 2, 14),
                    notice_period_required=30,
                    notice_period_served=20,
                    notice_status='Short',
                    status='Pending',
                    settlement_data={
                        "salaryForLastMonth": 38667,
                        "leaveEncashment": 11600,
                        "pendingLeaves": 6,
                        "gratuity": 103846,
                        "noticePeriodPayIn": 0,
                        "bonusDues": 8000,
                        "expenseReimbursement": 2000,
                        "noticePeriodRecovery": 19330,
                        "loanRecovery": 0,
                        "pfEmployee": 43200,
                        "pfEmployer": 43200,
                        "pfTotal": 86400,
                        "gratuityTaxExempt": 103846,
                        "tdsOnSettlement": 1200,
                        "assetRecovery": 0
                    },
                    exit_clearance=[]
                )
                db.session.add(fnf2)
                print(f"Seeded F&F for {emp2.full_name}")

        db.session.commit()
        print("Success: F&F seeding complete.")

if __name__ == "__main__":
    seed_fnf()
