import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.hr_documents import WFHRequest
from app import app
from datetime import date, datetime, timedelta
import random

def seed_wfh():
    with app.app_context():
        # Ensure table exists
        db.create_all()
        
        company = Company.query.first()
        if not company:
            print("❌ No company found.")
            return
            
        employees = Employee.query.filter_by(company_id=company.id).all()
        if not employees:
            print("❌ No employees found.")
            return

        print(f"🌱 Seeding WFH Requests for Company: {company.company_name}")
        
        reasons = [
            "Medical Emergency", 
            "Home Renovation", 
            "Internet Issues", 
            "Project Deadline", 
            "Personal Reason",
            "Childcare"
        ]
        statuses = ["PENDING", "APPROVED", "REJECTED", "PENDING", "APPROVED"]
        
        today = date.today()
        
        for emp in employees[:4]: # Seed for first 4 employees
            print(f"Seeding WFH for {emp.full_name}...")
            
            for i in range(3):
                from_date = today + timedelta(days=random.randint(-10, 10))
                duration = random.randint(1, 5)
                to_date = from_date + timedelta(days=duration)
                
                status = random.choice(statuses)
                
                request = WFHRequest(
                    company_id=company.id,
                    employee_id=emp.id,
                    employee_name=emp.full_name, # Mapping to "employee"
                    from_date=from_date,
                    to_date=to_date,
                    reason=random.choice(reasons),
                    status=status,
                    created_by=emp.user_id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 5))
                )
                
                if status != "PENDING":
                    request.action_by = 1 # Admin
                    request.action_at = datetime.utcnow()
                    if status == "REJECTED":
                        request.comments = "Rejected due to critical project deadline."
                
                db.session.add(request)
                
        db.session.commit()
        print("✅ WFH seeding completed successfully!")

if __name__ == "__main__":
    seed_wfh()
