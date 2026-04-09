from app import app, db
from models.user import User
from models.employee import Employee
from models.audit_log import AuditLog
from flask import g
import json
from unittest.mock import patch

# Mock decorators to skip token/permission checks during direct function testing
def mock_decorator(f):
    return f

with patch('utils.decorators.token_required', mock_decorator), \
     patch('utils.decorators.permission_required', lambda x: mock_decorator):
    
    from routes.audit_logs import get_audit_logs
    from routes.payroll import get_payroll_dashboard
    from routes.assets import asset_stats

    def verify():
        with app.app_context():
            manager_user_id = 20
            manager_user = User.query.get(manager_user_id)
            sub_user = User.query.get(33)
            
            g.user = manager_user
            
            print(f"--- VERIFYING AUDIT LOG FILTERING (as {manager_user.role}: {manager_user.email}) ---")
            with app.test_request_context():
                res = get_audit_logs()
                data = res[0].get_json() if isinstance(res, tuple) else res.get_json()
                print(f"Total Logs Visible: {data.get('total')}")
                # Print a few to check
                for l in data.get('data', [])[:3]:
                    print(f" - Log: {l.get('performer_name')} | Module: {l.get('module')}")

            print(f"\n--- VERIFYING PAYROLL DASHBOARD FILTERING (Month: 3 - March) ---")
            # Note: seed_dashboard typically seeds for past months. March 2026 should have data.
            with app.test_request_context('/?month=3&year=2026'):
                res = get_payroll_dashboard()
                data = res[0].get_json() if isinstance(res, tuple) else res.get_json()
                if data.get('success'):
                    summary = data.get('data', {}).get('summary', {})
                    print(f"Payroll Summary: {summary}")
                    # Should show processed/pending for team
                    runs = data.get('data', {}).get('recentRuns', [])
                    print(f"Recent Runs Count: {len(runs)}")
                else:
                    print(f"Payroll Dashboard Request Failed: {data.get('message')}")

            print(f"\n--- VERIFYING ASSETS ACCESS ---")
            with app.test_request_context():
                res = asset_stats()
                data = res[0].get_json() if isinstance(res, tuple) else res.get_json()
                print(f"Asset Stats: {data.get('stats')}")

    if __name__ == "__main__":
        verify()
