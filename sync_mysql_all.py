from app import app, db
from models.expense import ExpenseClaim
from models.loan import Loan
from models.training import TrainingProgram, TrainingParticipant, TrainingMaterial
from models.hr_documents import EsignRequest, EsignSettings
from datetime import datetime, date

def sync_all():
    with app.app_context():
        print("Syncing all tables to active database (MySQL)...")
        db.create_all()
        print("✅ Tables created or verified.")

        # Re-seed a few sample records for Loans & Expenses so the UI isn't empty
        print("Checking for existing loan data...")
        if Loan.query.count() == 0:
            print("Seeding sample loans...")
            # Using same sample data from SQLite seed
            sample_loan = Loan(
                company_id=1,
                employee_id=1,
                loan_type="Personal Loan",
                amount=250000.0,
                interest_rate=12.5,
                tenure_months=24,
                emi=11830.0,
                status="ACTIVE",
                disbursement_date=date(2023, 11, 15)
            )
            db.session.add(sample_loan)
            db.session.commit()
            print("✅ Sample loan seeded.")

        print("Checking for existing expense data...")
        if ExpenseClaim.query.count() == 0:
            print("Seeding sample expenses...")
            sample_exp = ExpenseClaim(
                company_id=1,
                employee_id=1,
                project_purpose="Client Visit NYC",
                category="Flight",
                amount=1200.0,
                currency="$",
                expense_date=date(2023, 10, 10),
                status="APPROVED",
                year=2023, month=10, day=10,
                time="14:30:00",
                added_by_name="Admin"
            )
            db.session.add(sample_exp)
            db.session.commit()
            print("✅ Sample expense seeded.")

        print("🚀 MySQL Sync & Seed Complete!")

if __name__ == "__main__":
    sync_all()
