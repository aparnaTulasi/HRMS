from app import app, db
from models.user import User
from models.permission import UserPermission
import traceback

def grant_payroll_permissions_to_managers():
    with app.app_context():
        print("Starting payroll permission update for Managers...")
        
        # Get all users with MANAGER role
        managers = User.query.filter_by(role='MANAGER').all()
        if not managers:
            print("No users with MANAGER role found.")
            return

        # Using direct strings as used in payroll_routes.py decorators
        payroll_permissions = [
            "PAYROLL_VIEW",
            "PAYROLL_CREATE",
            "PAYROLL_EDIT",
            "PAYROLL_GENERATE",
            "PAYROLL_APPROVE",
            "PAYROLL_EXPORT",
            "PAYROLL_REPORT"
        ]

        for manager in managers:
            print(f"--- Updating Payroll permissions for Manager: {manager.email} (ID: {manager.id}) ---")
            added_count = 0
            for perm_code in payroll_permissions:
                # Check if permission already exists
                exists = UserPermission.query.filter_by(
                    user_id=manager.id, 
                    permission_code=perm_code
                ).first()
                
                if not exists:
                    new_perm = UserPermission(
                        user_id=manager.id,
                        permission_code=perm_code
                    )
                    db.session.add(new_perm)
                    added_count += 1
            
            print(f"Added {added_count} new payroll permissions.")
        
        try:
            db.session.commit()
            print("Successfully updated Payroll permissions in the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    grant_payroll_permissions_to_managers()
