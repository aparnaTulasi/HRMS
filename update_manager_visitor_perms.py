from app import app, db
from models.user import User
from models.permission import UserPermission
from constants.permissions_registry import Permissions
import traceback

def grant_visitor_permissions_to_managers():
    with app.app_context():
        print("Starting permission update for Managers...")
        
        # Get all users with MANAGER role
        managers = User.query.filter_by(role='MANAGER').all()
        if not managers:
            print("No users with MANAGER role found.")
            return

        visitor_permissions = [
            Permissions.VISITOR_VIEW,
            Permissions.VISITOR_CREATE,
            Permissions.VISITOR_APPROVE,
            Permissions.VISITOR_LOG_MANAGE,
            Permissions.VISITOR_REPORT
        ]

        for manager in managers:
            print(f"--- Updating permissions for Manager: {manager.email} (ID: {manager.id}) ---")
            added_count = 0
            for perm_code in visitor_permissions:
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
            
            print(f"Added {added_count} new visitor permissions.")
        
        try:
            db.session.commit()
            print("Successfully updated permissions in the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    grant_visitor_permissions_to_managers()
