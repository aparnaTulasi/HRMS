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

def migrate_employees_permissions():
    with app.app_context():
        print("--- STARTING EMPLOYEE PBAC MIGRATION ---")
        
        # 1. Define permission blocks for each role
        ADMIN_PERMISSIONS = [
            Permissions.EMPLOYEE_VIEW,
            Permissions.EMPLOYEE_CREATE,
            Permissions.EMPLOYEE_EDIT,
            Permissions.EMPLOYEE_DELETE,
            Permissions.EMPLOYEE_STATUS_TOGGLE,
            Permissions.EMPLOYEE_IMPORT,
            Permissions.EMPLOYEE_EXPORT
        ]
        
        HR_PERMISSIONS = [
            Permissions.EMPLOYEE_VIEW,
            Permissions.EMPLOYEE_CREATE,
            Permissions.EMPLOYEE_EDIT,
            Permissions.EMPLOYEE_STATUS_TOGGLE
        ]
        
        # 2. Find all eligible users (EXCLUDING SUPER_ADMIN who has all)
        # We also filter for normalized roles
        users = User.query.filter(User.status == 'ACTIVE').all()
        
        count = 0
        for user in users:
            role = normalize_role(user.role)
            perms_to_add = []
            
            if role == 'ADMIN':
                perms_to_add = ADMIN_PERMISSIONS
            elif role == 'HR':
                perms_to_add = HR_PERMISSIONS
            
            if perms_to_add:
                # 3. Check for existing and add missing
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
    migrate_employees_permissions()
