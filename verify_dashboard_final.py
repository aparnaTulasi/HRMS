from app import app
from flask import g
import json

def verify_dashboard():
    with app.app_context():
        # Mock Super Admin User
        class MockUser:
            id = 1
            email = "admin@example.com"
            role = "SUPER_ADMIN"
            company_id = 1
            name = "Test Super Admin"
            
        g.user = MockUser()
        
        print("--- Testing /api/superadmin/dashboard-stats ---")
        from routes.superadmin import get_dashboard_stats
        with app.test_request_context('/api/superadmin/dashboard-stats', headers={'Authorization': 'Bearer test-token'}):
            resp_tuple = get_dashboard_stats()
            # Handle both tuple and single response object
            if isinstance(resp_tuple, tuple):
                resp, code = resp_tuple
            else:
                resp = resp_tuple
                code = 200
                
            data = resp.get_json()
            print(f"Full Data: {data}")
            print(f"Status Code: {code}")
            if data and data.get('success'):
                stats = data['data']['stats']
                print(f"Companies: {stats.get('total_companies')}")
                print(f"Employees: {stats.get('total_employees')}")
                print(f"Admins: {stats.get('total_admins')}")
                print(f"HRs: {stats.get('total_hrs')}")
                print(f"Alerts: {len(data['data']['system_alerts'])}")
            else:
                print(f"Error: {data.get('message')}")

        print("\n--- Testing /api/dashboard/stats ---")
        from routes.dashboard_routes import get_dashboard_stats as get_main_stats
        with app.test_request_context('/api/dashboard/stats', headers={'Authorization': 'Bearer test-token'}):
            resp2_val = get_main_stats()
            if isinstance(resp2_val, tuple):
                resp2, code2 = resp2_val
            else:
                resp2 = resp2_val
                code2 = 200
                
            data2 = resp2.get_json()
            if data2 and data2.get('success'):
                stats2 = data2['data']['stats']
                print(f"Companies: {stats2.get('total_companies')}")
                print(f"Employees: {stats2.get('total_employees')}")
                print(f"Pending Actions Total: {data2['data']['pending_actions']['total']}")
                print(f"Last Updated: {data2['data']['last_updated']}")
            else:
                print(f"Error in main stats: {data2.get('message')}")

if __name__ == "__main__":
    verify_dashboard()
