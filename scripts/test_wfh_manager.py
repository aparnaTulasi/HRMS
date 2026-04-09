import sys
import os
import json
from datetime import datetime, timedelta

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.hr_documents import WFHRequest
from flask import g
from unittest.mock import patch

# Mock decorators to bypass authentication/role checks for logic testing
patch('utils.decorators.token_required', lambda x: x).start()
patch('utils.decorators.role_required', lambda x: lambda y: y).start()

def test_wfh_manager_features():
    with app.app_context():
        # 1. Setup Manager and Team
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ Error: No Manager user found for testing.")
            return
            
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        team_member = Employee.query.filter_by(manager_id=manager_user.id).first()
        outsider = Employee.query.filter(Employee.manager_id != manager_user.id, Employee.manager_id.isnot(None)).first()

        if not team_member or not outsider:
            print("❌ Error: Need at least one team member and one outsider for scoped testing.")
            return

        g.user = manager_user
        print(f"--- Testing WFH Features for Manager: {manager_user.email} ---")
        print(f"Team Member: {team_member.full_name}, Outsider: {outsider.full_name}")

        # 2. Test WFH Allocation (Direct Assignment)
        from routes.wfh import allocate_wfh
        
        # A) Allocate to Team Member (Should SUCCEED)
        alloc_data = {
            "employee_id": team_member.id,
            "from_date": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "to_date": (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d'),
            "reason": "Project Deadline - Team Allocation"
        }
        with app.test_request_context(method='POST', json=alloc_data, headers={'Authorization': 'Bearer test'}):
            resp, code = allocate_wfh()
            if code == 201:
                print(f"✅ WFH Allocated to Team Member successfully.")
            else:
                print(f"❌ WFH Allocation Failed: {resp.get_json()}")

        # B) Allocate to Outsider (Should FAIL with 403)
        outsider_data = alloc_data.copy()
        outsider_data["employee_id"] = outsider.id
        with app.test_request_context(method='POST', json=outsider_data, headers={'Authorization': 'Bearer test'}):
            resp, code = allocate_wfh()
            if code == 403:
                print(f"✅ Security: Manager blocked from allocating to outsider (403).")
            else:
                print(f"❌ Security Failure: Manager allowed to allocate to outsider! Code: {code}")

        # 3. Test Team-Scoped Summary
        from routes.wfh import wfh_summary
        with app.test_request_context(headers={'Authorization': 'Bearer test'}):
            resp, code = wfh_summary()
            if code == 200:
                data = resp.get_json()['data']
                print(f"✅ Team Stats Fetched: Total={data['total_wfh']}, Approved={data['approved']}")
            else:
                print(f"❌ Summary Failed: {resp.get_json()}")

        # 4. Test Team-Scoped List
        from routes.wfh import list_wfh_requests
        with app.test_request_context(headers={'Authorization': 'Bearer test'}):
            resp, code = list_wfh_requests()
            requests = resp.get_json()['data']
            print(f"✅ Log Fetched: {len(requests)} items in team log.")
            # Verify no outsiders in log
            bad_data = [r for r in requests if r['employee_name'] == outsider.full_name]
            if not bad_data:
                print(f"✅ Security: No outsider records leaked in team log.")
            else:
                print(f"❌ Data Leak: Outsider record found in manager's log!")

        # 5. Test Export (Team Scoped)
        from routes.wfh import export_wfh_requests
        with app.test_request_context(headers={'Authorization': 'Bearer test'}):
            resp = export_wfh_requests()
            if resp.status_code == 200:
                print(f"✅ CSV Export generated successfully.")
            else:
                print(f"❌ CSV Export Failed.")

if __name__ == "__main__":
    test_wfh_manager_features()
