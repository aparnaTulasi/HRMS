from app import app
from models import db
from models.user import User
from sqlalchemy import text

def cleanup_final():
    with app.app_context():
        print("Starting FINAL cleanup (SuperAdmin & Companies only)...")
        
        # 1. Identify SuperAdmins
        sa_users = User.query.filter_by(role='SUPER_ADMIN').all()
        keep_user_ids = [u.id for u in sa_users]
        
        print(f"Keeping SuperAdmin User IDs: {keep_user_ids}")
        
        # 2. Disable Foreign Key Checks
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # Tables that depend on employee_id (delete ALL because NO employees are kept)
        emp_tables = [
            'attendance', 'loans', 'id_cards', 'leave_requests', 'leave_balances', 
            'leave_ledger', 'leave_encashments', 'leave_request_details', 'leave_approval_steps',
            'payroll', 'payslips', 'employee_address', 'employee_bank_details', 
            'employee_documents', 'employee_holiday_calendars', 'employee_onboarding_requests', 
            'employee_onboardings', 'employee_statutory', 'feedback', 'form16', 'full_and_final', 
            'hrm_documents', 'off_boarding', 'profile_change_approvals', 'profile_change_request_items', 
            'profile_change_requests', 'regularization', 'travel_expenses', 'wfh_requests',
            'employees' # Deleting all employees
        ]
        
        # 3. Clean up Employee-related
        for table in emp_tables:
            try:
                db.session.execute(text(f"DELETE FROM {table}"))
                print(f"Cleared table: {table}")
            except Exception as e:
                # print(f"Skipped {table}: {e}")
                pass
        
        # 4. Clean up User-related (except SuperAdmin)
        user_tables = [
            'user_permissions', 'audit_logs', 'notifications', 'otp_services', 'super_admins'
        ]
        
        for table in user_tables:
            try:
                if table == 'super_admins':
                     # Keep the SuperAdmin profiles too!
                     if keep_user_ids:
                        ids_str = ",".join(map(str, keep_user_ids))
                        db.session.execute(text(f"DELETE FROM super_admins WHERE user_id NOT IN ({ids_str})"))
                     else:
                        db.session.execute(text("DELETE FROM super_admins"))
                else:
                    if keep_user_ids:
                        ids_str = ",".join(map(str, keep_user_ids))
                        db.session.execute(text(f"DELETE FROM {table} WHERE user_id NOT IN ({ids_str}) AND user_id IS NOT NULL"))
                    else:
                        db.session.execute(text(f"DELETE FROM {table}"))
            except Exception as e:
                pass
        
        # 5. Delete from users (except SuperAdmin)
        if keep_user_ids:
            ids_str = ",".join(map(str, keep_user_ids))
            db.session.execute(text(f"DELETE FROM users WHERE id NOT IN ({ids_str})"))
        else:
            db.session.execute(text("DELETE FROM users"))
        print("Deleted extra users.")
        
        # NOTE: Companies are NOT in the emp_tables or user_tables lists, so they remain.
        
        # 6. Enable Foreign Key Checks
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        
        db.session.commit()
        print("FINAL Cleanup complete!")

if __name__ == "__main__":
    cleanup_final()
