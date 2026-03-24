from app import app
from routes.payroll import get_payroll_dashboard
from flask import request
import json

with app.app_context():
    # Mock request context
    with app.test_request_context('/admin/payroll/dashboard?month=5&year=2026'):
        # Mock g.user
        from flask import g
        class MockUser:
            id = 1
            role = "ADMIN"
            company_id = 1
        g.user = MockUser()
        
        try:
            response = get_payroll_dashboard()
            print("Response Code:", response[1])
            print("Response Data:", json.dumps(response[0].get_json(), indent=2))
        except Exception as e:
            print("Error:", e)
