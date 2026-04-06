from app import app, db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.permission import UserPermission
from flask import g
import json
from unittest.mock import patch

# Mock decorators before importing routes
def mock_decorator(f):
    return f

patch('utils.decorators.token_required', mock_decorator).start()
patch('utils.decorators.role_required', lambda x: mock_decorator).start()
patch('utils.decorators.permission_required', lambda x: mock_decorator).start()

def verify_invitation():
    with app.app_context():
        # 1. Setup
        company = Company.query.first()
        if not company:
            print("No company found.")
            return

        # Mock Super Admin
        class MockUser:
            id = 1
            role = "SUPER_ADMIN"
            company_id = company.id
        g.user = MockUser()

        email = "newmember_test@example.com"
        # Cleanup if exists
        u = User.query.filter_by(email=email).first()
        if u:
            Employee.query.filter_by(user_id=u.id).delete()
            UserPermission.query.filter_by(user_id=u.id).delete()
            db.session.delete(u)
            db.session.commit()

        # 2. Test Payload
        payload = {
            "full_name": "Vemireddy Venkateswara Reddy",
            "email": email,
            "password": "temporary_pass_123",
            "role": "MANAGER",
            "company_id": company.id,
            "branch_id": 1,
            "department": "Engineering",
            "permissions": {
                "Dashboard": ["VIEW"],
                "Employees": ["VIEW", "EDIT"],
                "Attendance": ["VIEW"]
            }
        }

        print("\n--- Testing Invitation Flow ---")
        from routes.permissions import invite_member_with_permissions
        with app.test_request_context('/api/superadmin/invite-member-with-permissions', 
                                   method='POST', 
                                   json=payload,
                                   headers={'Authorization': 'Bearer test-token'}):
            resp_tuple = invite_member_with_permissions()
            if isinstance(resp_tuple, tuple):
                resp, code = resp_tuple
            else:
                resp = resp_tuple
                code = 200
            
            data = resp.get_json()
            print(f"Status: {code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            if code == 201:
                # 3. Verify Database
                new_user = User.query.filter_by(email=email).first()
                new_emp = Employee.query.filter_by(user_id=new_user.id).first()
                perms = UserPermission.query.filter_by(user_id=new_user.id).all()

                print("\n--- Database Verification ---")
                print(f"User Created: {new_user is not None}")
                print(f"Employee ID: {new_emp.employee_id}")
                print(f"Branch ID: {new_emp.branch_id}")
                print(f"Permissions Count: {len(perms)}")
                for p in perms:
                    print(f"  Perm: {p.permission_code}")

if __name__ == "__main__":
    verify_invitation()
