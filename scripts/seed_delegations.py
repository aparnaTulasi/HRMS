import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.delegation import Delegation
from app import app
from datetime import date, timedelta
from sqlalchemy import text

def seed_delegations():
    with app.app_context():
        # FORCED DROP AND RECREATE to fix schema mismatch
        try:
            print("🗑️ Dropping delegations table for schema refresh...")
            db.session.execute(text('DROP TABLE IF EXISTS delegations'))
            db.session.commit()
            
            db.create_all()
            print("✅ Database tables created with NEW schema.")
        except Exception as ex:
            print(f"⚠️ schema refresh warning: {ex}")

        # Get Company
        company = Company.query.first()
        if not company:
            print("❌ No company found.")
            return
            
        employees = Employee.query.filter_by(company_id=company.id).all()
        if len(employees) < 2:
            print(f"❌ Not enough employees found (Found: {len(employees)})")
            return

        delegator = employees[0]
        delegatee = next((e for e in employees if e.id != delegator.id), None)
        
        if not delegatee:
            print("❌ No separate employee found to delegate to.")
            return
            
        print(f"🌱 Seeding Delegations for Company: {company.company_name} (ID: {company.id})")
        print(f"Delegator: {delegator.full_name} (ID: {delegator.id})")
        print(f"Delegatee: {delegatee.full_name} (ID: {delegatee.id})")

        today = date.today()
        
        delegations_data = [
            {
                "to_id": delegatee.id, 
                "module": "Leave Approvals", 
                "start": today, 
                "end": today + timedelta(days=7), 
                "status": "ACTIVE",
                "notes": "Delegating leave approvals while on vacation."
            },
            {
                "to_id": delegatee.id, 
                "module": "Expense Claims", 
                "start": today - timedelta(days=10), 
                "end": today - timedelta(days=3), 
                "status": "ACTIVE",
                "notes": "Delegated during last week's business trip."
            }
        ]
        
        try:
            for d in delegations_data:
                new_del = Delegation(
                    company_id=company.id,
                    delegated_by_id=delegator.id,
                    delegated_to_id=d['to_id'],
                    module=d['module'],
                    start_date=d['start'],
                    end_date=d['end'],
                    status=d['status'],
                    notes=d['notes']
                )
                db.session.add(new_del)
                
            db.session.commit()
            print("✅ Delegation seeding completed successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during seeding: {e}")

if __name__ == "__main__":
    seed_delegations()
