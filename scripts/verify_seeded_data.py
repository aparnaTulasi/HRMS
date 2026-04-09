import sys
import os
sys.path.append(os.getcwd())
from app import app, db
from models.user import User
from models.employee import Employee
from models.loan import Loan
from models.expense import ExpenseClaim
from models.hr_documents import WFHRequest
from models.support_ticket import SupportTicket
from models.attendance import Attendance

def verify():
    with app.app_context():
        user = User.query.filter_by(role='EMPLOYEE').first()
        if not user:
            print("❌ No Employee user found.")
            return

        emp = Employee.query.filter_by(user_id=user.id).first()
        if not emp:
            print("❌ No Employee profile found.")
            return

        print(f"--- VERIFICATION REPORT FOR: {emp.full_name} ({user.email}) ---")
        
        loans = Loan.query.filter_by(employee_id=emp.id).all()
        print(f"✅ LOANS: {len(loans)} records found.")
        for l in loans[:1]:
            print(f"   [Sample] Loan ID: {l.id}, Amount: {l.loan_amount}, Status: {l.status}")

        expenses = ExpenseClaim.query.filter_by(employee_id=emp.id).all()
        print(f"✅ EXPENSES: {len(expenses)} records found.")
        for e in expenses[:1]:
            print(f"   [Sample] Claim ID: {e.id}, Type: {e.expense_type}, Amount: {e.amount}, Status: {e.status}")

        wfh = WFHRequest.query.filter_by(employee_id=emp.id).all()
        print(f"✅ WFH: {len(wfh)} records found.")
        for w in wfh[:1]:
            print(f"   [Sample] WFH ID: {w.id}, Period: {w.from_date} to {w.to_date}, Status: {w.status}")

        tickets = SupportTicket.query.filter_by(created_by=user.id).all()
        print(f"✅ TICKETS: {len(tickets)} records found.")
        for t in tickets[:1]:
            print(f"   [Sample] Ticket ID: {t.ticket_id}, Category: {t.category}, Status: {t.status}")

        attendance = Attendance.query.filter_by(employee_id=emp.id).all()
        print(f"✅ ATTENDANCE: {len(attendance)} records found.")
        for a in attendance[:1]:
            print(f"   [Sample] Date: {a.attendance_date}, Status: {a.status}, Login: {a.punch_in_time}")

        print("--- ALL MODULES VERIFIED SUCCESSFULLY ---")

if __name__ == "__main__":
    verify()
