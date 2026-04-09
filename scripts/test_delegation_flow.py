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

# 1. Global Bypass for Auth Decorators
import utils.decorators
utils.decorators.token_required = lambda f: f
utils.decorators.role_required = lambda r: lambda f: f
utils.decorators.permission_required = lambda p: lambda f: f

def test_delegation_flow():
    with app.app_context():
        print("--- Testing Full Delegation Flow ---")
        
        # A. Identity Setup
        manager_user = User.query.filter_by(role='MANAGER').first()
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        
        # Find active Leave Delegation
        del_rec = Delegation.query.filter_by(
            delegated_by_id=manager_emp.id,
            module='Leave Approval',
            status='ACTIVE'
        ).first()
        
        if not del_rec:
            print("❌ No active leave delegation found. Please run seed_delegations_full.py first.")
            return

        delegate_emp = Employee.query.get(del_rec.delegated_to_id)
        delegate_user = User.query.get(delegate_emp.user_id)
        
        # Find a team member whose leave needs approval
        subordinate = Employee.query.filter_by(manager_id=manager_user.id).first()
        
        # B. Test 1: Delegate tries to approve leave
        print(f"Testing Delegate: {delegate_emp.full_name} acting for Manager: {manager_emp.full_name}")
        
        # Create a test leave request
        test_leave = LeaveRequest(
            company_id=manager_emp.company_id,
            employee_id=subordinate.id,
            leave_type_id=1,
            from_date=date.today(),
            to_date=date.today(),
            status='Pending'
        )
        db.session.add(test_leave)
        db.session.commit()
        
        with app.test_request_context():
            g.user = delegate_user
            from leave.routes import bulk_approval_action
            with patch('flask.request.get_json') as mock_json:
                mock_json.return_value = {"ids": [test_leave.id], "status": "Approved"}
                # Mock internal processing to focus on security logic
                import leave.routes
                leave.routes._process_leave_balance_deduction = MagicMock(return_value=(True, ""))
                leave.routes._sync_leave_to_attendance = MagicMock()
                
                resp, code = bulk_approval_action()
                if code == 200:
                    print(f"✅ Leave Approval Test Passed (Delegate Access).")
                else:
                    print(f"❌ Leave Approval Test Failed: {resp.get_json()}")

        # C. Test 2: Delegate tries to approve attendance regularization
        # (Assuming delegation for Attendance Approval also exists or using 'All')
        att_del = Delegation.query.filter_by(
            delegated_by_id=manager_emp.id,
            module='Attendance Approval',
            status='ACTIVE'
        ).first()
        
        if att_del:
            att_delegate_user = User.query.get(Employee.query.get(att_del.delegated_to_id).user_id)
            test_reg = AttendanceRegularization(
                company_id=manager_emp.company_id,
                employee_id=subordinate.id,
                attendance_date=date.today(),
                status='PENDING'
            )
            db.session.add(test_reg)
            db.session.commit()
            
            with app.test_request_context():
                g.user = att_delegate_user
                from routes.attendance import approve_regularization
                with patch('flask.request.get_json') as mock_json:
                    mock_json.return_value = {"approver_comment": "Approved through test delegation"}
                    resp, code = approve_regularization(test_reg.id)
                    if code == 200:
                        print(f"✅ Attendance Regularization Test Passed (Delegate Access).")
                    else:
                        print(f"❌ Attendance Regularization Test Failed: {resp.get_json()}")
            
            db.session.delete(test_reg)

        # D. Cleanup
        db.session.delete(test_leave)
        db.session.commit()
        print("--- Testing Complete ---")

if __name__ == "__main__":
    test_delegation_flow()
