import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.user import User
from models.permission import UserPermission
from constants.permissions_registry import Permissions
from utils.role_utils import normalize_role

def migrate_leave_permissions():
    """
    Auto-assign Leave Management permissions to existing roles.
    - ADMIN/HR: FULL access (VIEW, CREATE, EDIT, DELETE, APPROVE, REPORT)
    - MANAGER: VIEW, APPROVE
    """
    with app.app_context():
        print("--- STARTING LEAVE PBAC MIGRATION ---")
        
        ADMIN_HR_PERMS = [
            Permissions.LEAVE_VIEW,
            Permissions.LEAVE_CREATE,
            Permissions.LEAVE_EDIT,
            Permissions.LEAVE_DELETE,
            Permissions.LEAVE_APPROVE,
            Permissions.LEAVE_REPORT
        ]
        
        MANAGER_PERMS = [
            Permissions.LEAVE_VIEW,
            Permissions.LEAVE_APPROVE
        ]
        
        # EXCLUDING SUPER_ADMIN who has all perms automatically
        users = User.query.filter(User.status == 'ACTIVE').all()
        
        count = 0
        for user in users:
            role = normalize_role(user.role)
            perms_to_add = []
            
            if role in ['ADMIN', 'HR']:
                perms_to_add = ADMIN_HR_PERMS
            elif role == 'MANAGER':
                perms_to_add = MANAGER_PERMS
            
            if perms_to_add:
                # Check for existing and add missing
                existing_perms = [p.permission_code for p in UserPermission.query.filter_by(user_id=user.id).all()]
                
                for code in perms_to_add:
                    if code not in existing_perms:
                        new_perm = UserPermission(
                            user_id=user.id,
                            permission_code=code,
                            granted_by=1 # System/SuperAdmin
                        )
                        db.session.add(new_perm)
                        count += 1
        
        db.session.commit()
        print(f"--- MIGRATION COMPLETE: '{count}' User-Permission records added. ---")

if __name__ == "__main__":
    migrate_leave_permissions()
