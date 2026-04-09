from app import app, db
from models.user import User
from models.permission import UserPermission
from constants.permissions_registry import Permissions
import traceback

def grant_desk_permissions_to_managers():
    with app.app_context():
        print("Starting desk permission update for Managers...")
        
        # Get all users with MANAGER role
        managers = User.query.filter_by(role='MANAGER').all()
        if not managers:
            print("No users with MANAGER role found.")
            return

        desk_permissions = [
            Permissions.DESK_VIEW,
            Permissions.DESK_BOOK,
            Permissions.DESK_MANAGE
        ]

        for manager in managers:
            print(f"--- Updating Desk permissions for Manager: {manager.email} (ID: {manager.id}) ---")
            added_count = 0
            for perm_code in desk_permissions:
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
            
            print(f"Added {added_count} new desk permissions.")
        
        try:
            db.session.commit()
            print("Successfully updated Desk permissions in the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    grant_desk_permissions_to_managers()
