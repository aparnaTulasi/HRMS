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

def run_test_scenario():
    with app.app_context():
        print("=== STARTING HRMS E2E TEST SCENARIO SEEDING (FIXED V4) ===\n")
        
        # 1. Setup Company & Manager
        comp = Company.query.first()
        if not comp:
            print("Creating test company...")
            comp = Company(company_name="Test IT Solutions", has_attendance=True, has_leave=True, has_payroll=True)
            db.session.add(comp)
            db.session.commit()
        
        mgr_user = User.query.filter_by(role='MANAGER').first()
        if not mgr_user:
            print("Creating test manager user...")
            mgr_user = User(email="test_mgr@futureinvo.com", role="MANAGER", company_id=comp.id, password=generate_password_hash("test123"), status='ACTIVE', username="testmgr")
            db.session.add(mgr_user)
            db.session.commit()
        
        mgr_emp = Employee.query.filter_by(user_id=mgr_user.id).first()
        if not mgr_emp:
            print("Creating test manager employee profile...")
            mgr_emp = Employee(
                user_id=mgr_user.id,
                company_id=comp.id,
                full_name="Manager Sharma",
                employee_id="MGR-001",
                department="IT",
                designation="IT Manager",
                is_active=True
            )
            db.session.add(mgr_emp)
            db.session.commit()

        # 2. Create Software Engineer Employee
        emp_email = "engineer_test@futureinvo.com"
        existing_user = User.query.filter_by(email=emp_email).first()
        if existing_user:
            print(f"Cleaning up existing test user {emp_email}...")
            emp_ids = [e.id for e in Employee.query.filter_by(user_id=existing_user.id).all()]
            if emp_ids:
                Attendance.query.filter(Attendance.employee_id.in_(emp_ids)).delete(synchronize_session=False)
                LeaveRequest.query.filter(LeaveRequest.employee_id.in_(emp_ids)).delete(synchronize_session=False)
                PaySlip.query.filter(PaySlip.employee_id.in_(emp_ids)).delete(synchronize_session=False)
                LeaveBalance.query.filter(LeaveBalance.employee_id.in_(emp_ids)).delete(synchronize_session=False)
                Employee.query.filter_by(user_id=existing_user.id).delete()
            User.query.filter_by(id=existing_user.id).delete()
            db.session.commit()

        print("Creating Software Engineer 'Vijay Kumar' in IT Dept...")
        eng_user = User(
            email=emp_email, 
            role="EMPLOYEE", 
            company_id=comp.id, 
            password=generate_password_hash("test123"), 
            status='ACTIVE', 
            username="vijay_eng"
        )
        db.session.add(eng_user)
        db.session.flush()

        eng_emp = Employee(
            user_id=eng_user.id,
            company_id=comp.id,
            full_name="Vijay Kumar",
            employee_id="ENG-007",
            department="IT",
            designation="Software Engineer",
            manager_id=mgr_emp.id,
            date_of_joining=date.today() - timedelta(days=30),
            is_active=True,
            status='ACTIVE'
        )
        db.session.add(eng_emp)
        db.session.flush()

        # 3. Mark 5 Days Attendance (Present)
        print("Marking 5 days of attendance for Vijay...")
        for i in range(1, 6):
            att_date = date.today() - timedelta(days=i)
            if att_date.weekday() >= 5: continue
            
            att = Attendance(
                employee_id=eng_emp.id,
                company_id=comp.id,
                attendance_date=att_date,
                status="Present",
                punch_in_time=datetime.combine(att_date, datetime.min.time().replace(hour=9, minute=0)),
                punch_out_time=datetime.combine(att_date, datetime.min.time().replace(hour=18, minute=30)),
                year=att_date.year,
                month=att_date.month
            )
            db.session.add(att)

        # 4. Leave Management
        print("Setup Leave Type and Balance...")
        lt = LeaveType.query.filter_by(company_id=comp.id, code="SL").first()
        if not lt:
            lt = LeaveType(company_id=comp.id, code="SL", name="Sick Leave", unit="DAY")
            db.session.add(lt)
            db.session.flush()

        bal = LeaveBalance(employee_id=eng_emp.id, leave_type_id=lt.id, balance=10.0)
        db.session.add(bal)

        print("Applying for 2 days Sick Leave...")
        from_date = date.today() + timedelta(days=2)
        to_date = from_date + timedelta(days=1)
        
        lr = LeaveRequest(
            employee_id=eng_emp.id,
            company_id=comp.id,
            leave_type_id=lt.id,
            from_date=from_date,
            to_date=to_date,
            status="Approved",
            reason="Suffering from fever"
        )
        db.session.add(lr)

        # 5. Payroll (Generate Payslip for last month)
        print("Generating Payslip for last month...")
        last_month = date.today().replace(day=1) - timedelta(days=1)
        payslip = PaySlip(
            employee_id=eng_emp.id,
            company_id=comp.id,
            pay_month=last_month.month,
            pay_year=last_month.year,
            net_salary=53000.0,
            status="FINAL"
        )
        db.session.add(payslip)

        # 6. Recruitment (Post job and Onboard applicant)
        print("Creating Recruitment data...")
        job = JobPosting(
            job_title="Senior Full Stack Developer",
            company_id=comp.id,
            description="Looking for an expert in React and Python.",
            status="Open"
        )
        db.session.add(job)
        db.session.flush()

        applicant = JobApplicant(
            job_id=job.id,
            full_name="Rajesh Khanna",
            email="rajesh@example.com",
            current_stage="Hired"
        )
        db.session.add(applicant)

        db.session.commit()
        print("\n=== TEST SCENARIO SEEDED SUCCESSFULLY ===")
        print(f"Employee Email: {emp_email}")
        print(f"Password: test123")
        print(f"Company ID: {comp.id}")

if __name__ == "__main__":
    run_test_scenario()
