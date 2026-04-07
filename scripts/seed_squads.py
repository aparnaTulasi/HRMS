import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.squad import Squad
from models.squad_member import SquadMember
from models.attendance import Attendance
from app import app
from datetime import date, datetime, timedelta

def seed_squads():
    with app.app_context():
        db.create_all() # Ensure tables exist
        
        company = Company.query.first()
        if not company:
            print("❌ No company found.")
            return
            
        employees = Employee.query.filter_by(company_id=company.id).all()
        if len(employees) < 3:
            print(f"❌ Not enough employees found (Found: {len(employees)})")
            return

        print(f"🌱 Seeding Squad for Company: {company.company_name}")
        
        # 1. Create a Squad
        squad_name = "Super Alpha Team"
        existing_squad = Squad.query.filter_by(company_id=company.id, squad_name=squad_name).first()
        if not existing_squad:
            squad = Squad(
                company_id=company.id,
                squad_name=squad_name,
                project_name="HRMS Core Upgrade",
                department="Engineering",
                squad_type="Project Wise",
                status="Active"
            )
            db.session.add(squad)
            db.session.flush()
        else:
            squad = existing_squad

        # 2. Add members to the squad
        roles = ['Lead', 'Developer', 'Designer']
        for i, emp in enumerate(employees[:3]):
            existing_member = SquadMember.query.filter_by(squad_id=squad.id, employee_id=emp.id).first()
            if not existing_member:
                member = SquadMember(
                    squad_id=squad.id,
                    employee_id=emp.id,
                    role=roles[i % len(roles)]
                )
                db.session.add(member)
            
            # 3. Add attendance for today to make stats look good
            today = date.today()
            att = Attendance.query.filter_by(employee_id=emp.id, attendance_date=today).first()
            if not att:
                new_att = Attendance(
                    employee_id=emp.id,
                    company_id=company.id,
                    attendance_date=today,
                    status='Present',
                    punch_in_time=datetime.now()
                )
                db.session.add(new_att)

        db.session.commit()
        print(f"✅ Squad '{squad_name}' seeded successfully with {len(employees[:3])} members.")

if __name__ == "__main__":
    seed_squads()
