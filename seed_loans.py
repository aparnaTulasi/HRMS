from app import app
from models import db
from models.loan import Loan
from models.employee import Employee
from models.user import User
from datetime import datetime, date

def seed_loans():
    with app.app_context():
        db.create_all()
        # Seed for Company 3 (where Admin 6 and HR 7 are)
        TARGET_COMPANY_ID = 3
        
        # 1. Create/Find Employees if they don't exist
        names = ["Rajesh Kumar", "Sneha Patel", "Amit Singh", "Priya Sharma"]
        emps = []
        for name in names:
            emp = Employee.query.filter_by(full_name=name, company_id=TARGET_COMPANY_ID).first()
            if not emp:
                # Create dummy user first
                email = name.lower().replace(" ", ".") + "@example.com"
                user = User(email=email, password="password", role="EMPLOYEE", company_id=TARGET_COMPANY_ID, status="ACTIVE")
                db.session.add(user)
                db.session.flush()
                
                emp = Employee(
                    user_id=user.id,
                    company_id=TARGET_COMPANY_ID,
                    full_name=name,
                    employee_id=f"EMP-{user.id}",
                    designation="Staff"
                )
                db.session.add(emp)
                db.session.flush()
            emps.append(emp)

        # 2. Clear existing loans for consistency
        db.session.query(Loan).delete()

        # 3. Add loans matching UI
        loans_data = [
            {"emp": emps[0], "amount": 50000, "type": "Personal", "status": "ACTIVE", "emi": 5000, "interest": 8.5},
            {"emp": emps[1], "amount": 200000, "type": "Home Renovation", "status": "APPROVED", "emi": 10000, "interest": 9.0},
            {"emp": emps[2], "amount": 20000, "type": "Emergency", "status": "PAID", "emi": 4000, "interest": 8.0},
            {"emp": emps[3], "amount": 100000, "type": "Personal", "status": "PENDING", "emi": 8500, "interest": 8.5},
        ]

        for data in loans_data:
            loan = Loan(
                company_id=TARGET_COMPANY_ID,
                employee_id=data["emp"].id,
                loan_type=data["type"],
                amount=data["amount"],
                interest_rate=data["interest"],
                tenure_months=12,
                emi=data["emi"],
                status=data["status"],
                disbursement_date=date(2024, 3, 1) if data["status"] != "PENDING" else None
            )
            db.session.add(loan)

        # Add more active loans to reach count of 24 and total disbursed ₹12.5L
        current_sum = sum(d["amount"] for d in loans_data if d["status"] in ["ACTIVE", "APPROVED", "PAID"])
        remaining_sum = 1250000 - current_sum
        
        for i in range(23):
            loan = Loan(
                company_id=TARGET_COMPANY_ID,
                employee_id=emps[0].id,
                loan_type="Other",
                amount=remaining_sum / 23,
                interest_rate=8.5,
                tenure_months=12,
                emi=5000,
                status="ACTIVE",
                disbursement_date=date(2024, 2, 1)
            )
            db.session.add(loan)

        db.session.commit()
        print("Loan data seeded successfully for Company 3!")

if __name__ == "__main__":
    seed_loans()
