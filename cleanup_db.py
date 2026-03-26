from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.leave_requests import LeaveRequest
from models.loan import Loan
from models.id_card import IDCard
from models.super_admin import SuperAdmin

# Specific emails and employee IDs to keep
KEEP_EMAILS = [
    'aparnatulasi7@gamil.com',
    'aparnatulasi7@gmail.com',
    'seelamaparnatulasi@gmail.com',
    'jayadittakavi7@gmail.com',
    'seelamaparnatulasi7@gmail.com',
    'sandhya.rani@futureinvo.com',
    'sandhyarani@gmail.com'
]

KEEP_EMP_IDS = [
    'TL143-0001',
    'TL143-0002',
    'TL143-0003'
]

def cleanup():
    with app.app_context():
        print("Starting cleanup...")
        
        # 1. Identify Employees to KEEP
        keep_employees = Employee.query.filter(Employee.employee_id.in_(KEEP_EMP_IDS)).all()
        keep_emp_ids = [e.id for e in keep_employees]
        keep_user_ids_from_emp = [e.user_id for e in keep_employees]
        
        print(f"Keeping Employees: {[e.employee_id for e in keep_employees]}")
        
        # 2. Identify Users to KEEP
        keep_users = User.query.filter(User.email.in_(KEEP_EMAILS)).all()
        keep_user_ids_from_email = [u.id for u in keep_users]
        
        # Combined user IDs to keep
        all_keep_user_ids = list(set(keep_user_ids_from_emp + keep_user_ids_from_email))
        
        print(f"Keeping User IDs: {all_keep_user_ids}")
        
        # 3. Clean up related data first (Attendance, Loans, etc.)
        # These tables usually point to employees.
        try:
            Attendance.query.filter(~Attendance.employee_id.in_(keep_emp_ids)).delete(synchronize_session=False)
            print("Cleaned up attendance.")
        except Exception: print("Attendance cleanup skipped / not found.")

        try:
            # Check for other models that might have employee_id
            # Loan, IDCard, etc.
            Loan.query.filter(~Loan.employee_id.in_(keep_emp_ids)).delete(synchronize_session=False)
            print("Cleaned up loans.")
        except Exception: print("Loan cleanup skipped / not found.")

        # 4. Clean up Employees
        deleted_emps = Employee.query.filter(~Employee.id.in_(keep_emp_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_emps} extra employees.")
        
        # 5. Clean up SuperAdmins if they are not in the keep list
        # SuperAdmin refers to user_id
        try:
            deleted_sa = SuperAdmin.query.filter(~SuperAdmin.user_id.in_(all_keep_user_ids)).delete(synchronize_session=False)
            print(f"Deleted {deleted_sa} extra super admins.")
        except Exception: print("SuperAdmin cleanup skipped.")
        
        # 6. Clean up Users
        deleted_users = User.query.filter(~User.id.in_(all_keep_user_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_users} extra users.")
        
        db.session.commit()
        print("Cleanup complete!")

if __name__ == "__main__":
    cleanup()
