from app import app, db
from models.user import User
from models.employee import Employee
from flask import g
import json
from unittest.mock import patch

# Mock decorator
def mock_token_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

def get_res_json(res):
    if isinstance(res, tuple):
        return res[0].get_json()
    return res.get_json()

with patch('utils.decorators.token_required', mock_token_required), \
     patch('utils.decorators.role_required', lambda x: lambda f: f):
    
    from routes.admin import toggle_employee_status_admin

    def test_hierarchy():
        with app.app_context():
            print("\n=== TESTING TOGGLE HIERARCHY ===\n")
            
            # Setup Users for Testing in Company 1
            sa = User.query.filter_by(role='SUPER_ADMIN').first()
            admin = User.query.filter_by(role='ADMIN', company_id=1).first()
            hr = User.query.filter_by(role='HR', company_id=1).first()
            mgr = User.query.filter_by(role='MANAGER', company_id=1).first()
            emp = User.query.filter_by(role='EMPLOYEE', company_id=1).first()

            if not all([sa, admin, hr, mgr]):
                print("Missing users for hierarchy test. Run seeding first.")
                return

            def verify_toggle(actor, target, expected_code):
                g.user = actor
                target_emp = Employee.query.filter_by(user_id=target.id).first()
                if not target_emp:
                    print(f"No employee profile for {target.role}")
                    return
                
                with app.test_request_context():
                    res = toggle_employee_status_admin(target_emp.id)
                    status_code = res[1] if isinstance(res, tuple) else res.status_code
                    print(f"Actor: {actor.role} -> Target: {target.role} | Status Code: {status_code}")
                    if status_code != expected_code:
                        print(f"FAILED: Expected {expected_code}, got {status_code}")
                    else:
                        print("PASSED")

            # Test Cases
            print("1. Admin toggles HR (Same Company)")
            verify_toggle(admin, hr, 200)

            print("\n2. Admin toggles Super Admin")
            verify_toggle(admin, sa, 403)

            print("\n3. HR toggles Manager")
            verify_toggle(hr, mgr, 200)

            print("\n4. HR toggles Admin")
            verify_toggle(hr, admin, 403)

            print("\n5. Super Admin toggles anyone (Admin)")
            verify_toggle(sa, admin, 200)

    if __name__ == "__main__":
        test_hierarchy()
