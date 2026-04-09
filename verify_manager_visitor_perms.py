from app import app, db
from models.user import User
from models.permission import UserPermission
from constants.permissions_registry import Permissions

def verify_permissions():
    with app.app_context():
        print("Checking permissions for Managers...")
        managers = User.query.filter_by(role='MANAGER').all()
        
        visitor_perms = [
            Permissions.VISITOR_VIEW,
            Permissions.VISITOR_CREATE,
            Permissions.VISITOR_APPROVE,
            Permissions.VISITOR_LOG_MANAGE,
            Permissions.VISITOR_REPORT
        ]

        for manager in managers:
            print(f"\nManager: {manager.email} (ID: {manager.id})")
            user_perms = [p.permission_code for p in UserPermission.query.filter_by(user_id=manager.id).all()]
            
            missing = []
            for vp in visitor_perms:
                if vp not in user_perms:
                    missing.append(vp)
            
            if not missing:
                print("✅ All Visitor Management permissions present.")
            else:
                print(f"❌ Missing permissions: {', '.join(missing)}")

if __name__ == "__main__":
    verify_permissions()
