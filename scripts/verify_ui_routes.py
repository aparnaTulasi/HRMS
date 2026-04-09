import os
import sys
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.user import User
from flask import json

def test_routes():
    with app.test_client() as client:
        with app.app_context():
            # Find a manager/admin user
            user = User.query.filter(User.role.in_(['ADMIN', 'SUPER_ADMIN', 'MANAGER'])).first()
            if not user:
                print("No suitable user found for testing.")
                return

            print(f"Testing with User: {user.email} (Role: {user.role})")

            # Mock g.user using a session or by patching the decorator
            # For test_client, we usually need to generate a token or bypass auth
            # Here we will just perform raw requests and check for 404 vs 401/200
            
            # 1. Test Attendance Alias & Structure
            print("\n--- Testing Attendance ---")
            # We hit the base route to see if it's 401 (Auth working) vs 404 (Missing)
            res = client.get('/api/attendance/dashboard-stats')
            print(f"Base Attendance Stats: Status {res.status_code}")
            
            res = client.get('/api/admin/attendance/dashboard-stats')
            print(f"Admin Attendance Alias: Status {res.status_code}")

            res = client.get('/api/superadmin/attendance/dashboard-stats')
            print(f"SuperAdmin Attendance Alias: Status {res.status_code}")

            # 2. Test Travel Expenses Alias
            print("\n--- Testing Travel Expenses ---")
            res = client.get('/api/travel-expenses/stats')
            print(f"Travel Expenses Stats Alias: Status {res.status_code}")

            res = client.get('/api/travel-expenses/trends')
            print(f"Travel Expenses Trends Alias: Status {res.status_code}")

            # 3. Test Department Alias
            print("\n--- Testing Department Management ---")
            res = client.get('/api/department_management/list')
            print(f"Department Management Alias: Status {res.status_code}")

            # 4. Test Delegation Alias
            print("\n--- Testing Delegation Management ---")
            res = client.get('/api/administration/delegations/list')
            print(f"Delegation Management Alias: Status {res.status_code}")
            
            res = client.get('/api/administration/delegations/stats')
            print(f"Delegation Management Stats Alias: Status {res.status_code}")
            
if __name__ == "__main__":
    test_routes()
