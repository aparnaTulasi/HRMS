import sys
import os
import json
from datetime import datetime, date

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.delegation import Delegation
from leave.models import LeaveRequest
from models.attendance import AttendanceRegularization
from flask import g
from unittest.mock import patch, MagicMock

# Bypass auth for logic testing
import utils.decorators
utils.decorators.token_required = lambda f: f
utils.decorators.role_required = lambda r: lambda f: f
utils.decorators.permission_required = lambda p: lambda f: f

def test_delegation_logic():
    with app.app_context():
        # 1. Setup Manager and Delegatee
        manager_user = User.query.filter_by(role='MANAGER').first()
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        
        # Find who we delegated LEAVE to (from seeder)
        del_leave = Delegation.query.filter_by(
            delegated_by_id=manager_emp.id, 
            module='Leave Approval', 
            status='ACTIVE'
        ).first()
        
        if not del_leave:
            print("❌ No leave delegation found in DB.")
            return
            
        delegate_user = User.query.filter_by(id=del_leave.delegatee.user_id).first()
        
        # 2. Setup a Leave Request for the Manager's team
        subordinate = Employee.query.filter_by(manager_id=manager_user.id).first()
        if not subordinate:
            print("❌ No subordinate found for manager.")
            return
            
        # Create a pending leave request
        test_leave = LeaveRequest(
            company_id=manager_emp.company_id,
            employee_id=subordinate.id,
            leave_type_id=1,
            from_date=date.today(),
            to_date=date.today(),
            reason="Integration Test Leave",
            status="Pending"
        )
        db.session.add(test_leave)
        db.session.commit()

        print(f"--- Testing Delegation Integration ---")
        print(f"Manager: {manager_emp.full_name}")
        print(f"Delegate: {del_leave.delegatee.full_name}")
        print(f"Subordinate: {subordinate.full_name}")

        # 3. Test: Delegate tries to approve leave
        with app.test_request_context():
            g.user = delegate_user
            from leave.routes import bulk_approval_action
            
            with patch('flask.request.get_json') as mock_json:
                mock_json.return_value = {"ids": [test_leave.id], "status": "Approved"}
                # Mock _process_leave_balance_deduction and _sync_leave_to_attendance to avoid logic depth
                import leave.routes
                leave.routes._process_leave_balance_deduction = MagicMock(return_value=(True, ""))
                leave.routes._sync_leave_to_attendance = MagicMock()
                
                resp, code = bulk_approval_action()
                if code == 200:
                    res_data = resp.get_json()
                    if not res_data['errors']:
                        print("✅ Success: Delegate successfully approved leave request through delegation.")
                    else:
                        print(f"❌ Failure in approval: {res_data['errors']}")
                else:
                    print(f"❌ Failed to approve: {resp.get_json()}")

        # 4. Cleanup
        db.session.delete(test_leave)
        db.session.commit()

if __name__ == "__main__":
    test_delegation_logic()
