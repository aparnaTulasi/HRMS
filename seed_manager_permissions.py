from app import app, db
from models.user import User
from models.permission import UserPermission
from constants.permissions_registry import Permissions

def grant_manager_permissions():
    with app.app_context():
        managers = User.query.filter_by(role='MANAGER').all()
        if not managers:
            print("No users with 'MANAGER' role found.")
            return

        permissions_to_grant = [
            Permissions.PAYROLL_VIEW,
            Permissions.EMPLOYEE_VIEW,
            Permissions.AUDIT_VIEW,
            Permissions.ASSET_VIEW,
            Permissions.LEAVE_APPROVE, # Managers often need this
            Permissions.ATTENDANCE_APPROVE # And this
        ]

        print(f"Syncing permissions for {len(managers)} managers...")
        
        count = 0
        for user in managers:
            for perm_code in permissions_to_grant:
                # Check if already granted
                existing = UserPermission.query.filter_by(user_id=user.id, permission_code=perm_code).first()
                if not existing:
                    new_perm = UserPermission(
                        user_id=user.id,
                        permission_code=perm_code,
                        granted_by=1 # Assuming ID 1 is Super Admin
                    )
                    db.session.add(new_perm)
                    count += 1
        
        db.session.commit()
        print(f"Successfully granted {count} new permissions to Managers.")

if __name__ == "__main__":
    grant_manager_permissions()
