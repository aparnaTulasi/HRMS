import sys
import os
import json
from datetime import datetime

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from leave.models import LeaveRequest, LeaveType, LeavePolicy
from flask import g
from unittest.mock import patch

# Mock decorators to bypass authentication/permission checks
patch('utils.decorators.token_required', lambda x: x).start()
patch('utils.decorators.permission_required', lambda x: lambda y: y).start()

def test_leave_control_apis():
    with app.app_context():
        # Setup Test User (HR role for company-wide access)
        hr_user = User.query.filter_by(role='HR').first()
        if not hr_user:
            print("❌ Error: No HR user found for testing.")
            return
            
        g.user = hr_user
        print(f"--- Testing Leave Control APIs for HR: {hr_user.email} ---")

        # 1. Test Dashboard Stats
        from leave.routes import get_leave_dashboard_stats
        with app.test_request_context(headers={'Authorization': 'Bearer test'}):
            resp, code = get_leave_dashboard_stats()
            if code == 200:
                data = resp.get_json()
                print(f"✅ Dashboard Stats: Card Counts: {data['cards']}")
                print(f"✅ Dashboard Stats: Trends (12 mos): {data['monthly_trend']}")
                print(f"✅ Dashboard Stats: Distribution: {data['distribution']}")
            else:
                print(f"❌ Dashboard Stats Failed: {resp.get_json()}")

        # 2. Test Recent Requests
        from leave.routes import get_control_recent_requests
        with app.test_request_context(headers={'Authorization': 'Bearer test'}):
            resp, code = get_control_recent_requests()
            if code == 200:
                print(f"✅ Recent Requests Fetched. Count: {len(resp.get_json())}")
            else:
                print(f"❌ Recent Requests Failed: {resp.get_json()}")

        # 3. Test Policy Creation (Modal Logic)
        from leave.routes import manage_leave_policies
        policy_data = {
            'name': 'Test Sick Leave Policy',
            'days_per_year': 15,
            'description': 'Test policy created via API',
            'allow_carry_forward': True
        }
        with app.test_request_context(method='POST', json=policy_data, headers={'Authorization': 'Bearer test'}):
            resp, code = manage_leave_policies()
            if code == 201:
                print(f"✅ Policy Created: {resp.get_json()}")
            else:
                print(f"❌ Policy Creation Failed: {resp.get_json()}")

        # 4. Test Policy List
        with app.test_request_context(method='GET', headers={'Authorization': 'Bearer test'}):
            resp, code = manage_leave_policies()
            if code == 200:
                print(f"✅ Policies Fetched. Total: {len(resp.get_json())}")
            else:
                print(f"❌ Policy List Failed: {resp.get_json()}")

        # 5. Test Bulk Action
        from leave.routes import bulk_approval_action
        # Find 2 pending requests
        pending = LeaveRequest.query.filter_by(company_id=hr_user.company_id, status='Pending').limit(2).all()
        if len(pending) >= 1:
            bulk_data = {
                'ids': [p.id for p in pending],
                'status': 'Approved'
            }
            with app.test_request_context(method='POST', json=bulk_data, headers={'Authorization': 'Bearer test'}):
                resp, code = bulk_approval_action()
                if code == 200:
                    print(f"✅ Bulk Action Success: {resp.get_json()}")
                else:
                    print(f"❌ Bulk Action Failed: {resp.get_json()}")
        else:
            print("ℹ️ Skipping Bulk Action test (no pending requests found).")

if __name__ == "__main__":
    test_leave_control_apis()
