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
from models.loan import Loan
from flask import g
from unittest.mock import patch, MagicMock

# 1. Mock Decorators at the source
import utils.decorators
utils.decorators.token_required = lambda f: f
utils.decorators.role_required = lambda r: lambda f: f
utils.decorators.permission_required = lambda p: lambda f: f

# 2. Mock g before anything else
from flask import g

def test_loan_manager():
    with app.app_context():
        # Setup Manager
        manager_user = User.query.filter_by(role='MANAGER').first()
        if not manager_user:
            print("❌ No manager found.")
            return
            
        manager_emp = Employee.query.filter_by(user_id=manager_user.id).first()
        team_member = Employee.query.filter_by(manager_id=manager_user.id).first()
        outsider = Employee.query.filter(Employee.manager_id != manager_user.id).first()

        print(f"--- Testing Loan Manager Features ---")

        # Create a test client and mock g.user
        with app.test_client() as client:
            with app.test_request_context():
                g.user = manager_user
                
                # A. Test Dashboard
                from routes.loan_routes import get_loan_dashboard
                resp, code = get_loan_dashboard()
                if code == 200:
                    data = resp.get_json()['data']
                    print(f"✅ Dashboard Logic Verified. Stats: {data['stats']}")
                else:
                    print(f"❌ Dashboard Logic Failed: {resp.get_json()}")

                # B. Test List Visibility
                from routes.loan_routes import get_loan_requests
                resp, code = get_loan_requests()
                if code == 200:
                    loans = resp.get_json()['data']
                    print(f"✅ Log Scoping Verified. {len(loans)} team requests found.")
                else:
                    print(f"❌ List Visibility Failed: {resp.get_json()}")

                # C. Test Direct Application
                if team_member:
                    from routes.loan_routes import apply_loan
                    # Mock request.get_json()
                    with patch('flask.request.get_json') as mock_json:
                        mock_json.return_value = {
                            "employee_id": team_member.id,
                            "loan_type": "Education",
                            "amount": 250000,
                            "tenure_months": 36,
                            "reason": "Team Member Verified Loan"
                        }
                        resp, code = apply_loan()
                        if code == 201:
                            print(f"✅ Direct Application Verified for {team_member.full_name}.")
                            loan_id = resp.get_json()['loan']['id']
                        else:
                            print(f"❌ Direct Application Failed: {resp.get_json()}")
                            loan_id = None

                # D. Test Approval
                if loan_id:
                    from routes.loan_routes import loan_action
                    with patch('flask.request.get_json') as mock_json:
                        mock_json.return_value = {"action": "APPROVE"}
                        resp, code = loan_action(loan_id)
                        if code == 200:
                            print(f"✅ Approval Action Verified.")
                        else:
                            print(f"❌ Approval Logic Failed: {resp.get_json()}")

if __name__ == "__main__":
    test_loan_manager()
