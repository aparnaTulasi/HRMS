import sys
import os
import json
from flask import Flask

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.user import User
from models.permission import UserPermission
from models.employee import Employee
from models.company import Company
from werkzeug.security import generate_password_hash
import jwt
from datetime import datetime, timedelta
from config import Config
from constants.permissions_registry import Permissions

def test_employee_pbac_migration():
    with app.app_context():
        print("--- VERIFYING EMPLOYEE PBAC MIGRATION ---")
        
        # 1. Setup in-memory DB
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.create_all()
        
        client = app.test_client()
        comp = Company(subdomain='testcomp', company_name='Test Comp', company_code='TC01')
        db.session.add(comp)
        db.session.commit()
        
        # Scenario 1: HR with MIGRATED permissions
        hr = User(email='hr@test.com', password=generate_password_hash('pw123'), role='HR', company_id=comp.id, status='ACTIVE')
        db.session.add(hr)
        db.session.commit()
        
        # Manually add HR permissions (simulating migration script)
        hr_perms = [Permissions.EMPLOYEE_VIEW, Permissions.EMPLOYEE_CREATE, Permissions.EMPLOYEE_EDIT, Permissions.EMPLOYEE_STATUS_TOGGLE]
        for p in hr_perms:
            db.session.add(UserPermission(user_id=hr.id, permission_code=p))
        db.session.commit()
        
        # Scenario 2: Regular EMPLOYEE (no extra perms)
        emp = User(email='emp@test.com', password=generate_password_hash('pw123'), role='EMPLOYEE', company_id=comp.id, status='ACTIVE')
        db.session.add(emp)
        db.session.commit()
        
        emp_profile = Employee(user_id=emp.id, company_id=comp.id, employee_id='TC-0001', full_name='John Doe')
        db.session.add(emp_profile)
        db.session.commit()

        test_cases = [
            (hr, 'HR (with EMPLOYEE_VIEW)', '/api/admin/employees', 200, "HR should see employee list"),
            (hr, 'HR (checking EDIT)', f'/api/admin/employees/{emp_profile.id}', 200, "HR should see single employee"),
            (hr, 'HR (checking DELETE)', f'/api/admin/employees/{emp_profile.id}', 403, "HR should be BLOCKED from delete", 'DELETE'),
            (emp, 'EMPLOYEE (Self view)', '/api/admin/employees', 200, "Employee should see their own record (Self-view logic)"),
        ]
        
        for user, label, endpoint, expected_status, note, *method_args in test_cases:
            method = method_args[0] if method_args else 'GET'
            token = jwt.encode({
                'user_id': user.id,
                'role': user.role,
                'company_id': user.company_id,
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, Config.SECRET_KEY, algorithm="HS256")
            
            headers = {'Authorization': f'Bearer {token}'}
            
            if method == 'GET':
                resp = client.get(endpoint, headers=headers)
            elif method == 'DELETE':
                resp = client.delete(endpoint, headers=headers)
            
            print(f"Test case: {label:25} | Result Status: {resp.status_code} | Expected: {expected_status}")
            if resp.status_code != expected_status:
                print(f"   ❌ FAILED: {note}")
                if resp.status_code == 200 and expected_status == 200:
                    # check if list has data
                    data = resp.get_json()
                    print(f"   Data: {len(data.get('data', []))} items")
            else:
                print(f"   ✅ PASSED")
            
        print("\n--- PHASE 2 TEST COMPLETE ---")

if __name__ == "__main__":
    test_employee_pbac_migration()
