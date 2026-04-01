from app import app, db
from models.user import User
from models.employee import Employee
from models.company import Company
from models.attendance import Attendance
from models.payroll import PaySlip
from leave.models import LeaveRequest, LeaveBalance, LeaveType
from models.job_posting import JobPosting
from models.job_applicant import JobApplicant
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

def run_test_scenario_v5():
    with app.app_context():
        print("=== STARTING HRMS E2E TEST SCENARIO SEEDING (FOR COMPANY 1) ===\n")
        
        # 1. Use Company 1 (TEST LINE)
        target_company_id = 1
        comp = Company.query.get(target_company_id)
        if not comp:
            print(f"Company ID {target_company_id} not found. Using first available.")
            comp = Company.query.first()
            target_company_id = comp.id
        
        print(f"Targeting Company: {comp.company_name} (ID: {target_company_id})")

        # Ensure a Manager exists in THIS company
        mgr_user = User.query.filter_by(role='MANAGER', company_id=target_company_id).first()
        if not mgr_user:
            print("Creating manager for Company 1...")
            mgr_user = User(email=f"mgr_comp{target_company_id}@example.com", role="MANAGER", company_id=target_company_id, password=generate_password_hash("test123"), status='ACTIVE', username=f"mgr_test")
            db.session.add(mgr_user)
            db.session.commit()
        
        mgr_emp = Employee.query.filter_by(user_id=mgr_user.id).first()
        if not mgr_emp:
            mgr_emp = Employee(user_id=mgr_user.id, company_id=target_company_id, full_name="Test Manager", employee_id=f"MGR-C{target_company_id}", is_active=True)
            db.session.add(mgr_emp)
            db.session.commit()

        # 2. Cleanup and Create Test Users
        test_emails = ["vijay_test@example.com", "new_hire@example.com"]
        for email in test_emails:
            u = User.query.filter_by(email=email).first()
            if u:
                emp = Employee.query.filter_by(user_id=u.id).first()
                if emp:
                    # Deep cleanup of dependent logs
                    Attendance.query.filter_by(employee_id=emp.id).delete()
                    LeaveRequest.query.filter_by(employee_id=emp.id).delete()
                    PaySlip.query.filter_by(employee_id=emp.id).delete()
                    LeaveBalance.query.filter_by(employee_id=emp.id).delete()
                    Employee.query.filter_by(id=emp.id).delete()
                User.query.filter_by(id=u.id).delete()
        db.session.commit()

        print(f"Creating Software Engineer 'Vijay Kumar'...")
        emp_email = "vijay_test@example.com"
        eng_user = User(email=emp_email, role="EMPLOYEE", company_id=target_company_id, password=generate_password_hash("test123"), status='ACTIVE', username="vijay_eng")
        db.session.add(eng_user)
        db.session.flush()

        eng_emp = Employee(
            user_id=eng_user.id,
            company_id=target_company_id,
            full_name="Vijay Kumar",
            employee_id="ENG-999",
            department="IT",
            designation="Software Engineer",
            manager_id=mgr_emp.id,
            date_of_joining=date.today() - timedelta(days=30),
            is_active=True,
            onboarding_status='Completed'
        )
        db.session.add(eng_emp)
        db.session.flush()

        # 3. Attendance (Include TODAY)
        print("Marking attendance (including Today)...")
        for i in range(0, 5): # 0 is today
            att_date = date.today() - timedelta(days=i)
            if att_date.weekday() >= 5: continue
            att = Attendance(employee_id=eng_emp.id, company_id=target_company_id, attendance_date=att_date, status="Present", punch_in_time=datetime.combine(att_date, datetime.min.time().replace(hour=9, minute=0)))
            db.session.add(att)

        # 4. Onboarding Pending Sample
        print("Creating a Pending Onboarding employee...")
        pending_user = User(email="new_hire@example.com", role="EMPLOYEE", company_id=target_company_id, password=generate_password_hash("test123"), status='ACTIVE')
        db.session.add(pending_user)
        db.session.flush()
        
        pending_emp = Employee(user_id=pending_user.id, company_id=target_company_id, full_name="Fresh Graduate", employee_id="NEW-001", onboarding_status='Pending', is_active=True)
        db.session.add(pending_emp)

        # 5. Recruitment
        print("Creating Job and Applicants...")
        job = JobPosting(job_title="Software Architect", company_id=target_company_id, status="Open")
        db.session.add(job)
        db.session.flush()
        
        applicant = JobApplicant(job_id=job.id, full_name="Expert Dev", email="expert@example.com", current_stage="Hired")
        db.session.add(applicant)

        db.session.commit()
        print("\n=== E2E DATA SEEDED FOR REAL COMPANY CONTEXT ===")

if __name__ == "__main__":
    run_test_scenario_v5()
