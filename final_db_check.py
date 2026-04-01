from app import app, db
from models.employee import Employee
from models.attendance import Attendance
from models.job_posting import JobPosting

with app.app_context():
    print("=== DIRECT DATABASE CHECK (COMPANY ID 1) ===")
    
    # Check Employees
    emps = Employee.query.filter_by(company_id=1).all()
    print(f"Total Employees in Comp 1: {len(emps)}")
    for e in emps:
        print(f"- {e.full_name} (ID: {e.employee_id}, Status: {e.status}, Onboarding: {e.onboarding_status})")
    
    # Check Today's Attendance
    from datetime import date
    today = date.today()
    atts = Attendance.query.filter_by(company_id=1, attendance_date=today).all()
    print(f"\nAttendance Marked for Today: {len(atts)}")
    
    # Check Jobs
    jobs = JobPosting.query.filter_by(company_id=1).all()
    print(f"\nJob Postings: {len(jobs)}")
    for j in jobs:
        print(f"- {j.job_title} (Status: {j.status})")
