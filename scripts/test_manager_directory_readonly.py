import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from flask import g

def setup_test_data():
    with app.app_context():
        # Clear existing test data
        User.query.filter(User.email.like('dir_test_%')).delete(synchronize_session=False)
        db.session.commit()

        # Create Manager
        manager_user = User(email='dir_test_mgr@example.com', role='MANAGER', status='ACTIVE', company_id=1)
        db.session.add(manager_user)
        db.session.flush()
        
        manager_emp = Employee(user_id=manager_user.id, company_id=1, full_name='Directory Manager', employee_id='DMGR002')
        db.session.add(manager_emp)

        # Create another Employee to view/edit
        emp_user = User(email='dir_test_emp@example.com', role='EMPLOYEE', status='ACTIVE', company_id=1)
        db.session.add(emp_user)
        db.session.flush()
        
        emp_profile = Employee(user_id=emp_user.id, company_id=1, full_name='Target Employee', employee_id='DEMP002')
        db.session.add(emp_profile)
        
        db.session.commit()
        return manager_user.id, emp_profile.id

def test_manager_read_only(manager_user_id, target_emp_id):
    with app.app_context():
        g.user = User.query.get(manager_user_id)
        
        with app.test_request_context():
            from routes.admin import get_employees, get_employee, update_employee, deactivate_employee
            from routes.dashboard_routes import get_dashboard_stats
            
            # 1. Verify access to list
            resp, code = get_employees()
            print(f"List Employees status: {code}")
            assert code == 200
            
            # 2. Verify access to individual profile
            resp, code = get_employee(target_emp_id)
            print(f"View individual status: {code}")
            assert code == 200

            # 3. Verify statistics
            # We mock the g.user as it might not be fully populated in test_request_context by default
            g.user = User.query.get(manager_user_id)
            resp = get_dashboard_stats()
            data = resp.get_json()
            assert data['success'] is True
            assert 'directory_stats' in data['data']
            print(f"Directory Stats: {data['data']['directory_stats']}")

            # 4. Assert that Update is Forbidden
            import json
            with app.test_request_context(method='PUT', data=json.dumps({'full_name': 'Hacked Body'}), content_type='application_json'):
                g.user = User.query.get(manager_user_id)
                resp, code = update_employee(target_emp_id)
                print(f"Update attempt (other) status: {code}")
                # We updated the code to return 403 for any Manager update
                assert code == 403
            
            # 5. Assert that Self-Update is also Forbidden (as per latest request)
            manager_emp_id = Employee.query.filter_by(user_id=manager_user_id).first().id
            with app.test_request_context(method='PUT', data=json.dumps({'full_name': 'Manager Name Edit'}), content_type='application_json'):
                g.user = User.query.get(manager_user_id)
                resp, code = update_employee(manager_emp_id)
                print(f"Update attempt (self) status: {code}")
                assert code == 403

            # 6. Assert that Deactivate is Forbidden
            resp, code = deactivate_employee(target_emp_id)
            print(f"Deactivate attempt status: {code}")
            assert code == 403

            print("Manager Directory Read-Only tests PASSED.")

if __name__ == '__main__':
    mgr_id, target_id = setup_test_data()
    try:
        test_manager_read_only(mgr_id, target_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Test FAILED: {str(e)}")
    finally:
        print("Done.")
