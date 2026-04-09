from app import app, db
from models.user import User
from models.permission import UserPermission

def verify_payroll_permissions():
    with app.app_context():
        print("Checking Payroll permissions for Managers...")
        managers = User.query.filter_by(role='MANAGER').all()
        
        payroll_perms = [
            "PAYROLL_VIEW",
            "PAYROLL_CREATE",
            "PAYROLL_EDIT",
            "PAYROLL_GENERATE",
            "PAYROLL_APPROVE",
            "PAYROLL_EXPORT",
            "PAYROLL_REPORT"
        ]

        for manager in managers:
            print(f"\nManager: {manager.email} (ID: {manager.id})")
            user_perms = [p.permission_code for p in UserPermission.query.filter_by(user_id=manager.id).all()]
            
            missing = []
            for pp in payroll_perms:
                if pp not in user_perms:
                    missing.append(pp)
            
            if not missing:
                print("✅ All Payroll Management permissions present.")
            else:
                print(f"❌ Missing permissions: {', '.join(missing)}")

if __name__ == "__main__":
    verify_payroll_permissions()
