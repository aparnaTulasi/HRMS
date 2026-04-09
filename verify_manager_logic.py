from app import app, db
from models.user import User
from models.employee import Employee
from models.audit_log import AuditLog
from flask import g
import json

def verify():
    with app.app_context():
        # manager_user_id = 20
        # subordinate_user_id = 33
        # manager_emp_id = 15
        
        manager_user = User.query.get(20)
        sub_user = User.query.get(33)
        other_user = User.query.filter(User.id.notin_([20, 33])).first()
        
        print(f"--- VERIFYING AUDIT LOG FILTERING ---")
        from routes.audit_logs import get_audit_logs
        
        g.user = manager_user
        with app.test_request_context():
            res = get_audit_logs()
            data = res[0].get_json() if isinstance(res, tuple) else res.get_json()
            print(f"Manager ({manager_user.email}) view count: {data.get('total')}")
            
            # Check if any "other" users are in there
            logs = data.get('data', [])
            other_found = any(l.get('performer_name') != manager_user.name and l.get('performer_name') != sub_user.name for l in logs)
            print(f"Contains unauthorized users? {'YES (FAILED)' if other_found else 'NO (PASSED)'}")

        print(f"\n--- VERIFYING PAYROLL DASHBOARD FILTERING ---")
        from routes.payroll import get_payroll_dashboard
        
        with app.test_request_context():
            res = get_payroll_dashboard()
            data = res[0].get_json() if isinstance(res, tuple) else res.get_json()
            if data.get('success'):
                summary = data.get('data', {}).get('summary', {})
                print(f"Manager ({manager_user.email}) Payroll Summary: {summary}")
                # We expect the summary to reflect only 2 people (manager + 1 sub)
                print(f"Processed Count (Expected <= 2): {summary.get('processed')}")
            else:
                print(f"Payroll Dashboard Request Failed: {data.get('message')}")

        print(f"\n--- VERIFYING ASSETS ACCESS ---")
        from routes.assets import asset_stats
        with app.test_request_context():
            res = asset_stats()
            # print(res)
            status_code = res[1] if isinstance(res, tuple) else res.status_code
            print(f"Asset Stats Access: {'PASSED (200)' if status_code == 200 else f'FAILED ({status_code})'}")

if __name__ == "__main__":
    verify()
