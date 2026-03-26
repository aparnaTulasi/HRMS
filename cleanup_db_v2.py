from app import app
from models import db
from models.user import User
from models.employee import Employee
from sqlalchemy import text, inspect

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
        print("Starting cleanup (SQLAlchemy version)...")
        
        # 1. Get IDs to keep
        res_users = User.query.filter(User.email.in_(KEEP_EMAILS)).all()
        keep_user_ids = [u.id for u in res_users]
        
        res_emps = Employee.query.filter(Employee.employee_id.in_(KEEP_EMP_IDS)).all()
        keep_emp_ids = [e.id for e in res_emps]
        keep_user_ids_from_emp = [e.user_id for e in res_emps if e.user_id is not None]
        
        all_keep_user_ids = list(set(keep_user_ids + keep_user_ids_from_emp))
        
        print(f"Keeping User IDs: {all_keep_user_ids}")
        print(f"Keeping Employee IDs: {keep_emp_ids}")
        
        # 2. Disable Foreign Key Checks (Raw SQL is fine for this)
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # List of tables to clean up
        # We will use raw SQL for deletion but handle the list expansion ourselves
        emp_tables = [
            'attendance', 'loans', 'id_cards', 'leave_requests', 'leave_balances', 
            'leave_ledger', 'leave_encashments', 'leave_request_details', 'leave_approval_steps',
            'payroll', 'payslips', 'employee_address', 'employee_bank_details', 
            'employee_documents', 'employee_holiday_calendars', 'employee_onboarding_requests', 
            'employee_onboardings', 'employee_statutory', 'feedback', 'form16', 'full_and_final', 
            'hrm_documents', 'off_boarding', 'profile_change_approvals', 'profile_change_request_items', 
            'profile_change_requests', 'regularization', 'travel_expenses', 'wfh_requests'
        ]
        
        user_tables = [
            'super_admins', 'user_permissions', 'audit_logs', 'notifications', 'otp_services'
        ]
        
        def delete_extra(table, column, keep_list):
            if not keep_list:
                # If nothing to keep, delete everything
                sql = f"DELETE FROM {table}"
            else:
                # Manually join the list for the IN clause
                ids_str = ",".join(map(str, keep_list))
                sql = f"DELETE FROM {table} WHERE {column} NOT IN ({ids_str}) AND {column} IS NOT NULL"
            
            try:
                db.session.execute(text(sql))
            except Exception as e:
                # Table might not exist or column might not exist
                pass

        # Clean up Employee-related
        for table in emp_tables:
            delete_extra(table, 'employee_id', keep_emp_ids)
        
        # Delete from employees
        delete_extra('employees', 'id', keep_emp_ids)
        
        # Clean up User-related
        for table in user_tables:
            delete_extra(table, 'user_id', all_keep_user_ids)
            
        # Delete from users
        delete_extra('users', 'id', all_keep_user_ids)
        
        # 3. Enable Foreign Key Checks
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        
        db.session.commit()
        print("Cleanup complete!")

if __name__ == "__main__":
    cleanup()
