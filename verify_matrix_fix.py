from app import app, db
from models.user import User
from models.permission import UserPermission
from flask import g
import json

def verify_matrix_fix():
    with app.app_context():
        # 1. Test Modules List
        from routes.permissions import get_permission_modules
        with app.test_request_context('/api/superadmin/permissions/modules'):
            resp_data = get_permission_modules()
            if isinstance(resp_data, tuple): resp = resp_data[0]
            else: resp = resp_data
            data = resp.get_json()
            print("\n--- Modules API Response ---")
            print(f"Success: {data.get('success')}")
            print(f"Actions Sample: {data.get('data', {}).get('actions')[:3]}") # Should be ['View', 'Create', 'Edit']
            
        # 2. Test User Permissions Mapping
        sa = User.query.filter_by(role='SUPER_ADMIN').first()
        if sa:
            g.user = sa
            # Ensure dummy perm exists
            p = UserPermission.query.filter_by(user_id=sa.id, permission_code='DASHBOARD_VIEW').first()
            if not p:
                p = UserPermission(user_id=sa.id, permission_code='DASHBOARD_VIEW', granted_by=sa.id)
                db.session.add(p)
                db.session.commit()
            
            from routes.permissions import get_user_permissions
            with app.test_request_context(f'/api/superadmin/user-permissions/{sa.id}'):
                resp_data = get_user_permissions(sa.id)
                if isinstance(resp_data, tuple): resp = resp_data[0]
                else: resp = resp_data
                data = resp.get_json()
                print("\n--- User Permissions Mapping ---")
                perms = data.get('data', {}).get('permissions', {})
                print(f"Dashboard Perms: {perms.get('Dashboard')}") # Should be ['View']

if __name__ == "__main__":
    verify_matrix_fix()
