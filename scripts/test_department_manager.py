import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.department import Department
from flask import g

def setup_test_data():
    with app.app_context():
        # Clear existing test data
        User.query.filter(User.email.like('dept_test_%')).delete(synchronize_session=False)
        db.session.commit()

        # Create Manager
        manager_user = User(email='dept_test_mgr@example.com', role='MANAGER', status='ACTIVE')
        db.session.add(manager_user)
        db.session.flush()
        
        manager_emp = Employee(user_id=manager_user.id, company_id=1, full_name='Dept Manager', employee_id='DMGR001')
        db.session.add(manager_emp)
        db.session.flush()

        # Create Employee to assign
        emp_user = User(email='dept_test_emp@example.com', role='EMPLOYEE', status='ACTIVE')
        db.session.add(emp_user)
        db.session.flush()
        
        emp_profile = Employee(user_id=emp_user.id, company_id=1, full_name='Dept Employee', employee_id='DEMP001')
        db.session.add(emp_profile)
        
        db.session.commit()
        return manager_user.id, emp_profile.id

def test_manager_department_ops(manager_user_id, target_emp_id):
    with app.app_context():
        g.user = User.query.get(manager_user_id)
        
        with app.test_request_context():
            g.user = User.query.get(manager_user_id)
            from routes.department_routes import list_departments, create_department, assign_member_to_department
            
            # 1. List Departments
            resp, code = list_departments()
            print(f"List Departments status: {code}")
            assert code == 200

            # 2. Create Department
            import json
            from flask import request
            
            # Setup request data for create
            with app.test_request_context(method='POST', data=json.dumps({
                'department_name': 'Test New Dept',
                'location': 'Bangalore',
                'department_code': 'TND01'
            }), content_type='application_json'):
                g.user = User.query.get(manager_user_id)
                resp, code = create_department()
                data = resp.get_json()
                print(f"Create Department status: {code}, msg: {data.get('message')}")
                assert code == 201
                dept_id = data['id']

            # 3. Assign Member
            with app.test_request_context(method='POST', data=json.dumps({
                'employee_id': target_emp_id,
                'department_id': dept_id
            }), content_type='application_json'):
                g.user = User.query.get(manager_user_id)
                resp, code = assign_member_to_department()
                data = resp.get_json()
                print(f"Assign Member status: {code}, msg: {data.get('message')}")
                assert code == 200
                
                # Check employee profile
                emp = Employee.query.get(target_emp_id)
                assert emp.department == 'Test New Dept'
                print("Manager Department Operations PASSED.")

if __name__ == '__main__':
    mgr_id, emp_id = setup_test_data()
    try:
        test_manager_department_ops(mgr_id, emp_id)
    except Exception as e:
        print(f"Test FAILED: {str(e)}")
    finally:
        print("Done.")
