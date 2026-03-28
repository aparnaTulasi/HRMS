from app import app, db
from models.employee import Employee
from models.attendance import Attendance
from models.shift import Shift, ShiftAssignment
from models.task import Task
from models.payroll import PaySlip
from leave.models import LeaveRequest, LeaveBalance, Holiday, LeaveType
from datetime import datetime, date, time, timedelta
import traceback

def seed_dashboard():
    with app.app_context():
        print(f"Connecting to Database: {db.engine.url}")
        print("Seeding Dashboard Data for ALL Employees in MySQL...")
        
        emps = Employee.query.all()
        if not emps:
            print("No employees found. Skipping.")
            return

        for emp in emps:
            print(f"--- Seeding for Employee {emp.id} ({emp.full_name}) ---")
            
            try:
                # 1. Shift Assignments
                print("Seeding Shift (10 AM - 7 PM)...")
                shift = Shift.query.filter_by(shift_name="9 Hours General").first()
                if not shift:
                    shift = Shift(
                        company_id=emp.company_id,
                        shift_name="9 Hours General",
                        start_time=time(10, 0),
                        end_time=time(19, 0),
                        weekly_off="Sunday"
                    )
                    db.session.add(shift)
                    db.session.flush()
                
                assign = ShiftAssignment.query.filter_by(employee_id=emp.id).first()
                if not assign:
                    assign = ShiftAssignment(
                        company_id=emp.company_id,
                        employee_id=emp.id,
                        shift_id=shift.shift_id,
                        start_date=date(2023, 1, 1)
                    )
                    db.session.add(assign)

                # 2. Leave Balance (Optional/Defensive)
                try:
                    print("Seeding Leave Balance (12 Days)...")
                    ltype = LeaveType.query.filter_by(name="Privilege Leave").first()
                    if not ltype:
                        # Fallback: create one using raw SQL if model is suspect
                        db.session.execute("INSERT IGNORE INTO leave_types (company_id, name, code) VALUES (:cid, 'Privilege Leave', 'PL')", {"cid": emp.company_id})
                        db.session.commit()
                        ltype = LeaveType.query.filter_by(name="Privilege Leave").first()
                    
                    if ltype:
                        bal = LeaveBalance.query.filter_by(employee_id=emp.id, leave_type_id=ltype.id).first()
                        if not bal:
                            bal = LeaveBalance(employee_id=emp.id, leave_type_id=ltype.id, balance=12.0)
                            db.session.add(bal)
                        else:
                            bal.balance = 12.0
                except Exception as le:
                    print(f"⚠️ Warning: Could not seed Leave Balance: {le}")

                # 3. Tasks (3 Pending)
                print("Seeding 3 Tasks...")
                if Task.query.filter_by(assigned_to_employee_id=emp.id).count() < 3:
                    tasks = [
                        Task(company_id=emp.company_id, title="Compliance & Security Training", assigned_to_employee_id=emp.id, assigned_by_employee_id=emp.id, status="Pending"),
                        Task(company_id=emp.company_id, title="Update Profile Details", assigned_to_employee_id=emp.id, assigned_by_employee_id=emp.id, status="Pending"),
                        Task(company_id=emp.company_id, title="Submit Monthly Expense Report", assigned_to_employee_id=emp.id, assigned_by_employee_id=emp.id, status="Pending")
                    ]
                    db.session.add_all(tasks)

                # 4. Salary Trend (Last 5 Months)
                print("Seeding 5 Months of Payslips...")
                today = date.today()
                for i in range(1, 6):
                    target_date = today - timedelta(days=30*i)
                    y, m = target_date.year, target_date.month
                    
                    existing_ps = PaySlip.query.filter_by(employee_id=emp.id, pay_year=y, pay_month=m).first()
                    if not existing_ps:
                        amounts = [45000, 45000, 45000, 48000, 50000]
                        ps = PaySlip(
                            company_id=emp.company_id,
                            employee_id=emp.id,
                            pay_month=m,
                            pay_year=y,
                            net_salary=amounts[i-1],
                            status="PAID",
                            pay_date=target_date
                        )
                        db.session.add(ps)

                # 5. Holiday (Aug 15)
                try:
                    print("Seeding Holiday (Aug 15)...")
                    from leave.models import HolidayCalendar
                    cal = HolidayCalendar.query.filter_by(company_id=emp.company_id).first()
                    if not cal:
                        cal = HolidayCalendar(company_id=emp.company_id, name="Standard Calendar")
                        db.session.add(cal)
                        db.session.flush()
                    
                    holiday = Holiday.query.filter_by(date=date(2024, 8, 15)).first()
                    if not holiday:
                        holiday = Holiday(calendar_id=cal.id, company_id=emp.company_id, date=date(2024, 8, 15), name="Independence Day")
                        db.session.add(holiday)
                except Exception as he:
                    print(f"⚠️ Warning: Could not seed Holiday: {he}")

                db.session.commit()
                print(f"✅ Successfully seeded for Employee {emp.id}")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Failure seeding for Employee {emp.id}: {e}")
                traceback.print_exc()

    print("🚀 MySQL Dashboard Data Seeding process finished!")

if __name__ == "__main__":
    seed_dashboard()
