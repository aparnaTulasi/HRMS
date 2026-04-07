import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.visitor import VisitorRequest
from models.desk import Desk, DeskBooking
from app import app
from datetime import date, datetime

def seed_data():
    with app.app_context():
        # Get Company & Employee
        company = Company.query.first()
        if not company:
            print("❌ No company found. Please create a company first.")
            return
        
        employee = Employee.query.filter_by(company_id=company.id).first()
        if not employee:
            print("❌ No employee found. Please create an employee first.")
            return

        print(f"🌱 Seeding data for Company: {company.company_name} (ID: {company.id})")
        print(f"👤 Host Employee: {employee.full_name} (ID: {employee.id})")

        # 1. Seed Desks
        desks_data = [
            {"code": "D01", "floor": "1st Floor", "wing": "Alpha", "team": "Engineering", "perm": False},
            {"code": "D02", "floor": "1st Floor", "wing": "Alpha", "team": "Engineering", "perm": False},
            {"code": "D03", "floor": "2nd Floor", "wing": "Beta", "team": "Marketing", "perm": True},
            {"code": "D04", "floor": "2nd Floor", "wing": "Beta", "team": "Sales", "perm": False},
            {"code": "D05", "floor": "3rd Floor", "wing": "Gamma", "team": "HR", "perm": False},
        ]
        
        for d in desks_data:
            existing = Desk.query.filter_by(company_id=company.id, desk_code=d['code']).first()
            if not existing:
                new_desk = Desk(
                    company_id=company.id,
                    desk_code=d['code'],
                    location=f"Desk {d['code']}, {d['floor']} - {d['wing']} Wing",
                    floor=d['floor'],
                    wing=d['wing'],
                    team=d['team'],
                    is_permanent=d['perm'],
                    status='Available'
                )
                if d['perm']:
                    new_desk.assigned_employee_id = employee.id
                    new_desk.status = 'Assigned'
                db.session.add(new_desk)
        
        # 2. Seed Visitor Requests
        visitors_data = [
            {"name": "John Doe", "org": "Tech Corp", "purpose": "Software Demo", "status": "PENDING"},
            {"name": "Jane Smith", "org": "Marketing Hub", "purpose": "Client Meeting", "status": "APPROVED"},
            {"name": "Mike Ross", "org": "Law Firm", "purpose": "Legal Review", "status": "CHECKED_IN"},
        ]
        
        today = date.today()
        for v in visitors_data:
            existing = VisitorRequest.query.filter_by(company_id=company.id, visitor_name=v['name']).first()
            if not existing:
                new_v = VisitorRequest(
                    company_id=company.id,
                    visitor_name=v['name'],
                    organization=v['org'],
                    phone_number="+91 9999999999",
                    visit_date=today,
                    preferred_time="11:30 AM",
                    meeting_with_employee_id=employee.id,
                    purpose=v['purpose'],
                    status=v['status']
                )
                if v['status'] == 'CHECKED_IN':
                    new_v.check_in_time = datetime.now()
                db.session.add(new_v)
        
        db.session.commit()
        print("✅ Seeding completed successfully!")

if __name__ == "__main__":
    seed_data()
