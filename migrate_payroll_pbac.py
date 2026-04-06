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

def migrate_payroll_permissions():
    """
    Auto-assign Payroll & Compensation Management permissions to existing roles.
    - ADMIN/HR/ACCOUNT: FULL access
    (SUPER_ADMIN is bypassed globally in the decorators)
    """
    with app.app_context():
        print("--- STARTING PAYROLL PBAC MIGRATION ---")
        
        FULL_PERMS = [
            Permissions.PAYROLL_VIEW,
            Permissions.PAYROLL_CREATE,
            Permissions.PAYROLL_EDIT,
            Permissions.PAYROLL_GENERATE,
            Permissions.PAYROLL_APPROVE,
            Permissions.LOAN_MANAGEMENT,
            Permissions.EXPENSE_MANAGEMENT
        ]
        
        users = User.query.filter(User.status == 'ACTIVE').all()
        
        count = 0
        for user in users:
            role = normalize_role(user.role)
            perms_to_add = []
            
            # Note: The existing system often uses "ACCOUNT" instead of "ACCOUNTANT"
            if role in ['ADMIN', 'HR', 'ACCOUNT', 'ACCOUNTANT']:
                perms_to_add = FULL_PERMS
            
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
    migrate_payroll_permissions()
