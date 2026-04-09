import sys
import os
import unittest
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app import app, db
from models.user import User
from models.employee import Employee
from flask import g

class EmployeeModuleTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        
        # We need a context to find a real user
        with app.app_context():
            self.user = User.query.filter_by(role='EMPLOYEE').first()
            if not self.user:
                # Fallback to any user if no employee found
                self.user = User.query.first()
            
            if self.user:
                self.user_id = self.user.id
                print(f"Testing as User: {self.user.email} (Role: {self.user.role})")
            else:
                print("❌ ERROR: No user found in database to test with.")
                sys.exit(1)

    def test_01_my_team(self):
        print("\n[Testing My Team Dashboard]...")
        # Since token_required uses g.user, we need to mock it or provide a token.
        # Simplest is to bypass decorator by mocking g.user in a test helper
        with app.test_request_context():
            g.user = self.user
            from routes.team_routes import get_employee_team_dashboard
            res = get_employee_team_dashboard()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Squad: {data.get('squad_name')}")
            self.assertTrue(data.get('success'))

    def test_02_loans(self):
        print("\n[Testing Loans & Advances]...")
        with app.test_request_context():
            g.user = self.user
            from routes.loan_routes import list_loans
            res = list_loans()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Records: {len(data.get('data', []))}")
            self.assertTrue(data.get('success'))

    def test_03_expenses(self):
        print("\n[Testing Travel & Expenses]...")
        with app.test_request_context():
            g.user = self.user
            from routes.expense_routes import list_expense_claims
            res = list_expense_claims()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Records: {len(data.get('data', []))}")
            self.assertTrue(data.get('success'))

    def test_04_documents(self):
        print("\n[Testing Documents Center]...")
        with app.test_request_context():
            g.user = self.user
            from routes.document_center_routes import list_my_documents
            res = list_my_documents()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Records: {len(data.get('data', []))}")
            self.assertTrue(data.get('success'))

    def test_05_support(self):
        print("\n[Testing Support Helpdesk]...")
        with app.test_request_context():
            g.user = self.user
            from routes.support import get_tickets
            res = get_tickets()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Records: {len(data.get('data', []))}")
            self.assertTrue(data.get('success'))

    def test_06_attendance(self):
        print("\n[Testing My Attendance Log]...")
        with app.test_request_context():
            g.user = self.user
            from routes.attendance import my_attendance
            res = my_attendance()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Records: {len(data.get('attendance', []))}")
            self.assertTrue(data.get('success'))

    def test_07_wfh(self):
        print("\n[Testing WFH Requests]...")
        with app.test_request_context():
            g.user = self.user
            from routes.wfh import list_wfh_requests
            res = list_wfh_requests()
            data = res[0].get_json()
            print(f"Result: {data.get('success')} | Records: {len(data.get('data', []))}")
            self.assertTrue(data.get('success'))

if __name__ == "__main__":
    unittest.main(verbosity=2)
