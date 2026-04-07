import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from models import db
from models.company import Company
from models.employee import Employee
from models.attendance import Attendance
from app import app
from datetime import date, datetime, timedelta
import random

def seed_attendance():
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

        print(f"🌱 Seeding Attendance Logs for Company: {company.company_name}")
        
        today = date.today()
        
        # Seed for last 30 days
        for i in range(30):
            att_date = today - timedelta(days=i)
            
            # Skip Sundays for realism
            if att_date.weekday() == 6:
                continue
                
            for emp in employees:
                # Check if already exists
                existing = Attendance.query.filter_by(
                    employee_id=emp.id, 
                    attendance_date=att_date
                ).first()
                
                if not existing:
                    # Randomize status
                    rand = random.random()
                    status = "Present"
                    if rand > 0.95: 
                        status = "Absent"
                    elif rand > 0.85:
                        status = "Half Day"
                    
                    punch_in = None
                    punch_out = None
                    
                    if status != "Absent":
                        # Standard 9 AM to 6 PM with random variance
                        in_hour = 9 if random.random() > 0.3 else 10
                        in_min = random.randint(0, 59)
                        punch_in = datetime(att_date.year, att_date.month, att_date.day, in_hour, in_min)
                        
                        out_hour = 18 if status == "Present" else 13
                        out_min = random.randint(0, 59)
                        punch_out = datetime(att_date.year, att_date.month, att_date.day, out_hour, out_min)

                    log = Attendance(
                        company_id=company.id,
                        employee_id=emp.id,
                        attendance_date=att_date,
                        year=att_date.year,
                        month=att_date.month,
                        status=status,
                        punch_in_time=punch_in,
                        punch_out_time=punch_out,
                        capture_method="Biometric",
                        created_by=1 # System/Admin
                    )
                    db.session.add(log)
                    
        db.session.commit()
        print("✅ Attendance seeding completed successfully!")

if __name__ == "__main__":
    seed_attendance()
