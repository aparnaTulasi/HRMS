from app import app, db
from models.user import User
from flask import g
import json
from unittest.mock import patch

# Mock decorator
def mock_token_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

def get_res_json(res):
    if isinstance(res, tuple):
        return res[0].get_json()
    return res.get_json()

with patch('utils.decorators.token_required', mock_token_required), \
     patch('utils.decorators.role_required', lambda x: lambda f: f):
    
    from routes.dashboard_routes import get_dashboard_stats

    def verify():
        with app.app_context():
            print("\n=== VERIFYING E2E TEST RESULTS IN DASHBOARD ===\n")
            
            # 1. Verify as Manager (Team Stats)
            mgr_user = User.query.filter_by(role='MANAGER', email='test_mgr@futureinvo.com').first()
            if mgr_user:
                g.user = mgr_user
                with app.test_request_context():
                    res = get_dashboard_stats()
                    data = get_res_json(res)
                    print("MANAGER DASHBOARD SNAPSHOT:")
                    print(json.dumps(data.get('data', {}).get('team_snapshot', {}), indent=2))
                    print("\nPENDING LEAVES FOR MANAGER:")
                    print(json.dumps(data.get('data', {}).get('pending_leaves', []), indent=2))

            # 2. Verify as HR (Organization Stats)
            hr_user = User.query.filter_by(role='HR').first()
            if hr_user:
                g.user = hr_user
                with app.test_request_context():
                    res = get_dashboard_stats()
                    data = get_res_json(res)
                    print("\nHR DASHBOARD SNAPSHOT (Company Health):")
                    print(json.dumps(data.get('data', {}).get('company_health', {}), indent=2))
                    print("\nRECRUITMENT DATA FOR HR:")
                    print(json.dumps(data.get('data', {}).get('onboarding_pending', []), indent=2))

    if __name__ == "__main__":
        verify()
