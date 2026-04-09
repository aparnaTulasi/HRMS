import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from leave.models import LeaveRequest
from datetime import date, timedelta, datetime
from flask import g
from unittest.mock import patch

# Mock decorators to bypass JWT/Permission checks in tests
patch('utils.decorators.token_required', lambda x: x).start()
patch('utils.decorators.permission_required', lambda x: lambda y: y).start()

def test_leave_management_access():
    with app.app_context():
        # --- TEST 1: Manager Access ---
        manager_user = User.query.filter_by(role='MANAGER').first()
        if manager_user:
            print(f"--- Testing Leave APIs for Manager: {manager_user.email} ---")
            g.user = manager_user
            
            # Test Stats
            from leave.routes import get_leave_dashboard_stats
            with app.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                g.user = manager_user  # Set inside context
                resp, code = get_leave_dashboard_stats()
                if code == 200:
                    print(f"✅ Manager Stats fetched: {resp.get_json()}")
                else:
                    print(f"❌ Manager Stats failed (Code: {code}): {resp.get_json()}")
            
            # Test Pending List
            from leave.routes import get_pending_approvals
            with app.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                g.user = manager_user  # Set inside context
                resp, code = get_pending_approvals()
                if code == 200:
                    print(f"✅ Manager Pending List fetched. Count: {len(resp.get_json())}")
                else:
                    print(f"❌ Manager Pending List failed (Code: {code}): {resp.get_json()}")

        # --- TEST 2: HR Access ---
        hr_user = User.query.filter_by(role='HR').first()
        if hr_user:
            print(f"\n--- Testing Leave APIs for HR: {hr_user.email} ---")
            
            # Test Stats
            with app.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                g.user = hr_user
                resp, code = get_leave_dashboard_stats()
                if code == 200:
                    print(f"✅ HR Stats fetched: {resp.get_json()}")
                else:
                    print(f"❌ HR Stats failed (Code: {code}): {resp.get_json()}")
            
            # Test Pending List
            with app.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                g.user = hr_user
                resp, code = get_pending_approvals()
                if code == 200:
                    print(f"✅ HR Pending List fetched. Count: {len(resp.get_json())}")
                else:
                    print(f"❌ HR Pending List failed (Code: {code}): {resp.get_json()}")

        # --- TEST 3: Security Check (Manager approving non-team request) ---
        if manager_user:
            print("\n--- Testing Security: Manager approving non-team leave ---")
            
            # Find a leave request NOT belonging to this manager's team
            sub_ids = [e.id for e in Employee.query.filter_by(manager_id=manager_user.id).all()]
            other_leave = LeaveRequest.query.filter(LeaveRequest.employee_id.notin_(sub_ids)).first()
            
            if other_leave:
                from leave.routes import approve_leave
                with app.test_request_context(method='POST', json={'status': 'Approved'}, headers={'Authorization': 'Bearer test-token'}):
                    g.user = manager_user
                    resp, code = approve_leave(other_leave.id)
                    if code == 403:
                        print(f"✅ Security Check Passed: Manager blocked from approving non-team request.")
                    else:
                        print(f"❌ Security Check Failed: Manager allowed to approve non-team request (Code: {code})")
            else:
                print("ℹ️ Skipping security test (no non-team requests found).")

if __name__ == "__main__":
    test_leave_management_access()
