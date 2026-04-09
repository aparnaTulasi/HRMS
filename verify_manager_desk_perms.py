from app import app, db
from models.user import User
from models.permission import UserPermission
from constants.permissions_registry import Permissions

def verify_desk_permissions():
    with app.app_context():
        print("Checking Desk permissions for Managers...")
        managers = User.query.filter_by(role='MANAGER').all()
        
        desk_perms = [
            Permissions.DESK_VIEW,
            Permissions.DESK_BOOK,
            Permissions.DESK_MANAGE
        ]

        for manager in managers:
            print(f"\nManager: {manager.email} (ID: {manager.id})")
            user_perms = [p.permission_code for p in UserPermission.query.filter_by(user_id=manager.id).all()]
            
            missing = []
            for dp in desk_perms:
                if dp not in user_perms:
                    missing.append(dp)
            
            if not missing:
                print("✅ All Desk Management permissions present.")
            else:
                print(f"❌ Missing permissions: {', '.join(missing)}")

if __name__ == "__main__":
    verify_desk_permissions()
