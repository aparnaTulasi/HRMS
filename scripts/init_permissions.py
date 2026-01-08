# scripts/init_permissions.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models.permission import Permission
from models.urls import SystemURL
import json

def init_permissions():
    with app.app_context():
        print("Ensuring all database tables are created...")
        db.create_all()
        
        # Default permissions
        permissions = [
            ('VIEW_EMPLOYEE_DETAILS', 'View employee details', 'EMPLOYEE'),
            ('EDIT_EMPLOYEE', 'Edit employee information', 'EMPLOYEE'),
            ('VIEW_ATTENDANCE', 'View attendance records', 'ATTENDANCE'),
            ('EDIT_ATTENDANCE', 'Edit attendance records', 'ATTENDANCE'),
            ('MANAGE_USERS', 'Manage users and permissions', 'ADMIN'),
            ('MANAGE_COMPANY', 'Manage company settings', 'ADMIN'),
        ]
        
        for code, desc, module in permissions:
            if not Permission.query.filter_by(permission_code=code).first():
                perm = Permission(
                    permission_code=code,
                    description=desc,
                    module=module
                )
                db.session.add(perm)
        
        # Default URLs
        urls = [
            ('employee_list', '/employees', 'Employee List', 'EMPLOYEE', ['ADMIN', 'HR', 'MANAGER']),
            ('attendance_dashboard', '/attendance', 'Attendance Dashboard', 'ATTENDANCE', ['ADMIN', 'HR', 'MANAGER']),
            ('profile', '/profile', 'My Profile', 'EMPLOYEE', ['EMPLOYEE', 'ADMIN', 'HR', 'MANAGER']),
            ('admin_dashboard', '/admin', 'Admin Dashboard', 'ADMIN', ['ADMIN']),
        ]
        
        for code, path, desc, module, roles in urls:
            if not SystemURL.query.filter_by(url_code=code).first():
                url = SystemURL(
                    url_code=code,
                    url_path=path,
                    description=desc,
                    module=module,
                    allowed_roles=json.dumps(roles),
                    is_active=True,
                    is_public=False
                )
                db.session.add(url)
        
        db.session.commit()
        print("✅ Permissions and URLs initialized!")

if __name__ == '__main__':
    init_permissions()