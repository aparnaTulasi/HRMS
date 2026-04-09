import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance, AttendanceRegularization
from models.shift import Shift
from datetime import date, timedelta, datetime
from flask import g

def test_manager_attendance():
    # Using imported app
    with app.app_context():
        # 1. Find a Manager and their Team
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ No Manager found in database.")
            return

        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        if not manager_emp:
            print("❌ Manager employee profile not found.")
            return

        print(f"--- Testing Attendance APIs for Manager: {manager_emp.full_name} (ID: {manager_emp.id}) ---")

        # Mock g.user
        g.user = manager_user

        # 2. Test Dashboard Stats
        from routes.attendance import dashboard_stats
        with app.test_request_context():
            response, status_code = dashboard_stats()
            data = response.get_json()
            if status_code == 200:
                print("✅ Attendance Dashboard Stats fetched successfully.")
                print(f"   Summary: {data['summary']}")
                print(f"   Today's Overview Count: {len(data['overview'])}")
            else:
                print(f"❌ Failed to fetch Dashboard Stats: {data}")

        # 3. Test Bulk List
        from routes.attendance import bulk_list_attendance_employees
        today_str = date.today().strftime("%Y-%m-%d")
        with app.test_request_context(query_string={'date': today_str}):
            response, status_code = bulk_list_attendance_employees()
            data = response.get_json()
            if status_code == 200:
                print(f"✅ Bulk Attendance List fetched successfully. Total subordinates: {len(data['employees'])}")
            else:
                print(f"❌ Failed to fetch Bulk List: {data}")

        # 4. Test Regularization Pending
        from routes.attendance import pending_regularization_requests
        with app.test_request_context():
            response, status_code = pending_regularization_requests()
            data = response.get_json()
            if status_code == 200:
                print(f"✅ Pending Regularization Requests fetched successfully. Count: {len(data['pending'])}")
            else:
                print(f"❌ Failed to fetch Pending Regularization: {data}")

        # 5. Test Authorization (Edge Case)
        # Find a regularization request NOT belonging to this manager's team
        subordinate_ids = [e.id for e in Employee.query.filter_by(manager_id=manager_emp.id).all()]
        other_req = AttendanceRegularization.query.filter(AttendanceRegularization.employee_id.notin_(subordinate_ids)).first()
        
        if other_req:
            from routes.attendance import approve_regularization
            with app.test_request_context(json={'approver_comment': 'Hack attempt'}):
                response, status_code = approve_regularization(other_req.id)
                data = response.get_json()
                if status_code == 403:
                    print(f"✅ Security Check Passed: Manager blocked from approving non-team request (Response: {data['message']})")
                else:
                    print(f"⚠️ Security Check Failed: Manager allowed to approve non-team request (Status: {status_code})")
        else:
            print("ℹ️ Skipping security check (no non-team requests found).")

        print("\n--- Attendance API Verification Complete ---")

if __name__ == "__main__":
    test_manager_attendance()
