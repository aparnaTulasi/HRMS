import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.support_ticket import SupportTicket
from app import app
from datetime import date, datetime, timedelta

def seed_support():
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

        print(f"🌱 Seeding Support Tickets for Company: {company.company_name}")
        
        categories = ["IT Support", "Payroll", "HR Query", "Office Admin"]
        priorities = ["Low", "Medium", "High", "Urgent"]
        statuses = ["Open", "In Progress", "Resolved", "Open"]
        
        # Add a few tickets for the first few employees
        for i, emp in enumerate(employees[:2]):
            print(f"Ticket seeding for {emp.full_name}...")
            
            for j in range(3):
                # Unique ID: SUP-empID-seq
                ticket_id = f"SUP-{emp.id}{j:02d}"
                
                existing = SupportTicket.query.filter_by(ticket_id=ticket_id).first()
                if not existing:
                    ticket = SupportTicket(
                        ticket_id=ticket_id,
                        subject=f"Help needed with {categories[j % len(categories)]}",
                        category=categories[j % len(categories)],
                        priority=priorities[j % len(priorities)],
                        status=statuses[j % len(statuses)],
                        description=f"Detailed description for sample ticket {ticket_id}.",
                        company_id=company.id,
                        created_by=emp.user_id # SupportTicket uses users.id
                    )
                    db.session.add(ticket)
                
        db.session.commit()
        print("✅ Support seeding completed successfully!")

if __name__ == "__main__":
    seed_support()
